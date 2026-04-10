#define ROCKY_CUDA_API

#include <rocky20/api/rocky_api.h>
#include <rocky20/api/rocky_api_sph.h>
#include <rocky20/api/device/api_backend.hpp>
#include <rocky20/api/sph/api_cuda_sph.hpp>

static std::vector<std::string> ROI_names;

struct ROIData 
{
    int index;
    double reference_point_x;
    double reference_point_y;
    double reference_point_z;
};

/* Structure with local module variables */
struct ModuleData
{
    double start_time;                        // time to start the freezing procedure
    int n_ROIs{0};
    ROIData* roi_data;
};

/* Define module name and version (same as the one in the *.plugin file)*/
ROCKY_PLUGIN("SPH Spray Nozzle (Beta)", "1.0.0")
ROCKY_PLUGIN_SPH()


/* Hook used to retrieve input parameter values entered via the Rocky UI 
(defined in the Python specification file)*/
ROCKY_PLUGIN_CONFIGURE(input_data, data)
{
    ROCKY_MESSAGE_LOG("SPH Spray Nozzle Addin: configure");
    /* Allocate memory for module local variables */
    ModuleData *module_data = new ModuleData();

    /* Access Rocky data model to retrieve input parameter values */

    auto model_properties = input_data.get_model();

    module_data->start_time = model_properties.get_double("spray_start_time");
    module_data->n_ROIs =  model_properties.get_list_size("active_regions");
    module_data->roi_data = new ROIData[module_data->n_ROIs];

    for (int i = 0; i < module_data->n_ROIs; ++i)
    {
        auto region_data = model_properties.get_list_item("active_regions", i);

        std::string name = region_data.get_string("roi_name");
        module_data->roi_data[i].reference_point_x = region_data.get_double("reference_point_x");
        module_data->roi_data[i].reference_point_y = region_data.get_double("reference_point_y");
        module_data->roi_data[i].reference_point_z = region_data.get_double("reference_point_z");
        ROI_names.push_back(name);
    }

    /* Cast module structure pointer to a generic pointer for internal handling */
    data = static_cast<void *>(module_data);   
}

ROCKY_PLUGIN_INITIALIZE(model, _data)
{   ROCKY_INFO_LOG("SPH Spray Nozzle Addin: initialize");
    auto data = static_cast<ModuleData*>(_data);
    auto sph_model = get_sph_model(model);

    for(int i = 0; i < data->n_ROIs; i++)
    {
        int index = sph_model.get_sph_element_scalars().find(ROI_names[i].c_str());
        if (index < 0)
            ROCKY_RUNTIME_ERROR("SPH Spray Nozzle module misconfiguration, missing ROI \"" << ROI_names[i] << "\".");

        data->roi_data[i].index = index;
    }
}

/* Hook used to allocate resources for the module */
ROCKY_PLUGIN_SETUP(model, _data)
{
    ROCKY_MESSAGE_LOG("SPH Spray Nozzle Addin: setup");

    /* Cast data to local structure */
    auto module_data = static_cast<ModuleData *>(_data);

    /* Add a new scalar variable to the SPH scalar's pool */
}


/* Hook used to nondimensionalize local variables */
ROCKY_PLUGIN_NON_DIMENSIONALIZE(model, data)
{
    ROCKY_INFO_LOG("SPH Spray Nozzle Addin: non-dimensionalize");
    /* Cast data to local structure */
    ModuleData *module_data = static_cast<ModuleData *>(data);

    /* Scale local variables by the corresponding factor */
    module_data->start_time /= model.get_time_factor();

    for(int i = 0; i < module_data->n_ROIs; i++)
    {
        module_data->roi_data[i].reference_point_x /= model.get_length_factor();
        module_data->roi_data[i].reference_point_y /= model.get_length_factor();
        module_data->roi_data[i].reference_point_z /= model.get_length_factor();
    }
}

ROCKY_PLUGIN_INITIALIZE_CUDA(model, host_data, device_id, _device_data)
{
    ROCKY_INFO_LOG("SPH Spray Nozzle Addin: initialize_cuda");
    auto h_data {static_cast<ModuleData *>(host_data)};
    auto d_data {*h_data};
    int size = h_data->n_ROIs;
    
    d_data.roi_data = nullptr;
    CUDA_MALLOC_TYPE(d_data.roi_data, size, ROIData);
    CUDA_COPY_H2D(d_data.roi_data, h_data->roi_data, size);
    
    ModuleData *device_copy {nullptr};
    CUDA_MALLOC_TYPE(device_copy, 1, ModuleData);
    CUDA_COPY_H2D(device_copy, &d_data, 1);
    _device_data = static_cast<void *>(device_copy);
}

ROCKY_PLUGIN_POST_FORCE_ON_SPH_ELEMENTS(device_model, sph_model, sph_element, _data)
{
    auto data = static_cast<ModuleData*>(_data);

    if (device_model.get_current_time() < data->start_time) return;
    
    /* Get SPH elements scalars */
    auto element_scalars = sph_element.get_scalars();

    for(int i = 0; i < data->n_ROIs; i++)
    {   
        bool inside_roi = element_scalars.get_scalar<bool>(data->roi_data[i].index);

        if(!inside_roi) continue;

        float3 nozzle_position = {data->roi_data[i].reference_point_x, data->roi_data[i].reference_point_y, data->roi_data[i].reference_point_z};
        float3 el_proj_direction = sph_element.get_position() - nozzle_position;
        el_proj_direction /= get_norm(el_proj_direction);
        
        float3 el_velocity = sph_element.get_velocity();
        float3 el_new_velocity = dot(el_velocity, el_proj_direction) * el_proj_direction;

        float3 acceleration = (el_new_velocity - el_velocity) / sph_model.get_sph_timestep();

        sph_element.add_acceleration(acceleration);
    }

}
ROCKY_PLUGIN_POST_FORCE_ON_SPH_ELEMENTS_END()

ROCKY_PLUGIN_TEAR_DOWN(model, module_data)
{
    ROCKY_INFO_LOG("SPH Spray Nozzle Addin: plugin tear down");
    ModuleData *data = static_cast<ModuleData *>(module_data);
    if (data->roi_data)
        delete[] data->roi_data;
    delete data;
}

ROCKY_PLUGIN_TEAR_DOWN_CUDA(model, device_id, device_data)
{   ROCKY_INFO_LOG("SPH Spray Nozzle Addin: plugin tear down cuda");
    auto d_data = static_cast<ModuleData *>(device_data); 
    ModuleData data_ptrs;
    CUDA_COPY_D2H(&data_ptrs, d_data, 1);
    CUDA_FREE(data_ptrs.roi_data);
    CUDA_FREE(d_data);
}

ROCKY_PLUGIN_SPH_END()

ROCKY_PLUGIN_END