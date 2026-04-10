
#define ROCKY_CUDA_API
#include <rocky20/api/rocky_api.h>
#include <rocky20/api/device/api_backend.hpp>

static std::vector<std::string> roi_names;
static std::vector<std::string> pointcloud_names;

struct Data
{
    int particle_scalar_index;
    double activate_total_time;
    double activate_delay_time;

    double fluid_density;
    double fluid_viscosity;
    double factor;
    double distance_multiplier;

    bool* activate_sensor;

    int n_list_itens;
    int n_particle_groups;
    int* ROI_index;
    int* pointcloud_index;
    int* u_index;
    int* v_index;
    int* w_index;
    int* flag_start;
    double* start_time_with_delay;
    double* final_time_with_delay;
};

ROCKY_PLUGIN("Air Knife Actuator Sensor", "1.0.0")

ROCKY_PLUGIN_CONFIGURE(input_data, data)
{
    Data *plugin_data = new Data();
    
    plugin_data->fluid_density   = input_data.get_model().get_double("fluid_density");
    plugin_data->fluid_viscosity = input_data.get_model().get_double("fluid_viscosity");
    plugin_data->factor = input_data.get_model().get_double("factor");
    plugin_data->distance_multiplier = input_data.get_model().get_double("distance_multiplier");
    plugin_data->activate_total_time = input_data.get_model().get_double("activate_total_time");
    plugin_data->activate_delay_time = input_data.get_model().get_double("activate_delay_time");

    plugin_data->n_list_itens = input_data.get_model().get_list_size("sensor_pointcloud_list");
    plugin_data->ROI_index = new int[plugin_data->n_list_itens]();
    plugin_data->pointcloud_index = new int[plugin_data->n_list_itens]();
    plugin_data->u_index = new int[plugin_data->n_list_itens]();
    plugin_data->v_index = new int[plugin_data->n_list_itens]();
    plugin_data->w_index = new int[plugin_data->n_list_itens]();
    plugin_data->flag_start = new int[plugin_data->n_list_itens]();
    plugin_data->start_time_with_delay = new double[plugin_data->n_list_itens]();
    plugin_data->final_time_with_delay = new double[plugin_data->n_list_itens]();

    for (int i = 0; i < plugin_data->n_list_itens; ++i)
    {
        auto item_data = input_data.get_model().get_list_item("sensor_pointcloud_list", i);

        std::string name1 = item_data.get_string("roi_name");
        roi_names.push_back(name1);

        std::string name2 = item_data.get_string("point_cloud");
        pointcloud_names.push_back(name2);
    }

    plugin_data->n_particle_groups = input_data.get_number_particle_groups();
    plugin_data->activate_sensor = new bool[plugin_data->n_particle_groups]();
    for (int i = 0; i < plugin_data->n_particle_groups; ++i)
    {
        auto particle_data = input_data.get_particle_group_data(i);
        plugin_data->activate_sensor[i] = particle_data.get_bool("activate_sensor");
    }
    
    data = static_cast<void *>(plugin_data);
}

ROCKY_PLUGIN_SETUP(model, _data)
{
    auto data = static_cast<Data*>(_data);

    for (int i = 0; i < data->n_list_itens; ++i)
    {
        data->pointcloud_index[i] = model.find_point_cloud(pointcloud_names[i].c_str());
        data->u_index[i] = model.find_point_cloud_property(data->pointcloud_index[i], "u");
        data->v_index[i] = model.find_point_cloud_property(data->pointcloud_index[i], "v");
        data->w_index[i] = model.find_point_cloud_property(data->pointcloud_index[i], "w");
    }

    auto scalars = model.get_particle_scalars();
    data->particle_scalar_index = scalars.add("Fluid Force", "N");
}

ROCKY_PLUGIN_INITIALIZE(model, _data)
{
    auto data = static_cast<Data*>(_data);

    for (int i = 0; i < data->n_list_itens; ++i)
    {
        int index = model.get_particle_scalars().find(roi_names[i].c_str());
        if (index < 0)
            ROCKY_RUNTIME_ERROR("Module misconfiguration, missing ROI \"" << roi_names[i] << "\".");
        data->ROI_index[i] = index;
    }
}

ROCKY_PLUGIN_NON_DIMENSIONALIZE(model, _data)
{
    auto data = static_cast<Data *>(_data);

    for (int i = 0; i < data->n_list_itens; ++i)
    {
        model.set_point_cloud_property_dimension(
            data->pointcloud_index[i], data->u_index[i], model.get_length_factor() / model.get_time_factor() );
        model.set_point_cloud_property_dimension(
            data->pointcloud_index[i], data->v_index[i], model.get_length_factor() / model.get_time_factor() );
        model.set_point_cloud_property_dimension(
            data->pointcloud_index[i], data->w_index[i], model.get_length_factor() / model.get_time_factor() );
    }

    data->fluid_density   /= model.get_mass_factor() / pow(model.get_length_factor(), 3);
    data->fluid_viscosity /= model.get_pressure_factor() * model.get_time_factor();
    data->activate_total_time /= model.get_time_factor();
    data->activate_delay_time /= model.get_time_factor();

    auto particle_scalar = model.get_particle_scalars();
    particle_scalar.set_dimension(data->particle_scalar_index, model.get_force_factor());
}

ROCKY_PLUGIN_TEAR_DOWN(model, _data)
{
    Data* data = static_cast<Data *>(_data);
    if (data->ROI_index)
        delete[] data->ROI_index;
    if (data->pointcloud_index)
        delete[] data->pointcloud_index;
    if (data->u_index)
        delete[] data->u_index;
    if (data->v_index)
        delete[] data->v_index;
    if (data->w_index)
        delete[] data->w_index;
    if (data->activate_sensor)
        delete[] data->activate_sensor;
    if (data->flag_start)
        delete[] data->flag_start;
    if (data->start_time_with_delay)
        delete[] data->start_time_with_delay;
    if (data->final_time_with_delay)
        delete[] data->final_time_with_delay;
    delete data;
}

ROCKY_PLUGIN_INITIALIZE_CUDA(model, host_data, device_id, _device_data)
{
    auto h_data = static_cast<Data*>(host_data);
    auto d_data = *h_data;

    int size1 = h_data->n_particle_groups;
    d_data.activate_sensor = nullptr;
    CUDA_MALLOC_TYPE(d_data.activate_sensor, size1, bool);
    CUDA_COPY_H2D(d_data.activate_sensor, h_data->activate_sensor, size1);

    int size2 = h_data->n_list_itens;
    d_data.ROI_index = nullptr;
    CUDA_MALLOC_TYPE(d_data.ROI_index, size2, int);
    CUDA_COPY_H2D(d_data.ROI_index, h_data->ROI_index, size2);

    d_data.pointcloud_index = nullptr;
    CUDA_MALLOC_TYPE(d_data.pointcloud_index, size2, int);
    CUDA_COPY_H2D(d_data.pointcloud_index, h_data->pointcloud_index, size2);

    d_data.u_index = nullptr;
    CUDA_MALLOC_TYPE(d_data.u_index, size2, int);
    CUDA_COPY_H2D(d_data.u_index, h_data->u_index, size2);

    d_data.v_index = nullptr;
    CUDA_MALLOC_TYPE(d_data.v_index, size2, int);
    CUDA_COPY_H2D(d_data.v_index, h_data->v_index, size2);

    d_data.w_index = nullptr;
    CUDA_MALLOC_TYPE(d_data.w_index, size2, int);
    CUDA_COPY_H2D(d_data.w_index, h_data->w_index, size2);

    d_data.flag_start = nullptr;
    CUDA_MALLOC_TYPE(d_data.flag_start, size2, int);
    CUDA_COPY_H2D(d_data.flag_start, h_data->flag_start, size2);

    d_data.start_time_with_delay = nullptr;
    CUDA_MALLOC_TYPE(d_data.start_time_with_delay, size2, double);
    CUDA_COPY_H2D(d_data.start_time_with_delay, h_data->start_time_with_delay, size2);

    d_data.final_time_with_delay = nullptr;
    CUDA_MALLOC_TYPE(d_data.final_time_with_delay, size2, double);
    CUDA_COPY_H2D(d_data.final_time_with_delay, h_data->final_time_with_delay, size2);

    Data *device_data = nullptr;
    CUDA_MALLOC_TYPE(device_data, 1,Data);
    CUDA_COPY_H2D(device_data, &d_data, 1);
    _device_data = static_cast<void *>(device_data);
}

ROCKY_PLUGIN_TEAR_DOWN_CUDA(model, device_id, device_data)
{
    auto d_data = static_cast<Data*>(device_data);
    Data data_ptrs;
    CUDA_COPY_D2H(&data_ptrs, d_data, 1);
    CUDA_FREE(data_ptrs.ROI_index);
    CUDA_FREE(data_ptrs.pointcloud_index);
    CUDA_FREE(data_ptrs.u_index);
    CUDA_FREE(data_ptrs.v_index);
    CUDA_FREE(data_ptrs.w_index);
    CUDA_FREE(data_ptrs.activate_sensor);
    CUDA_FREE(data_ptrs.flag_start);
    CUDA_FREE(data_ptrs.start_time_with_delay);
    CUDA_FREE(data_ptrs.final_time_with_delay);
    CUDA_FREE(d_data);
}

// FUNCTION: DRAG FORCE CALCULATION ("Schiller & Neumann" Correlation):
inline ROCKY_FUNCTIONS double calculate_drag_force(
    double density, double viscosity, double diameter, double velocity_r)
{
    double area = M_PI * (diameter * diameter) / 4;
    double Re = (density / viscosity) * abs(velocity_r) * diameter;
    double Cd = max(24 / Re * ( 1 + 0.15 * pow(Re, 0.687)) , 0.44 );
    return 0.5 * Cd * density * area * abs(velocity_r) * velocity_r;
}


ROCKY_PLUGIN_POST_FORCE_ON_PARTICLES(model, particle, _data)
{
    auto data = static_cast<Data *>(_data);

    auto particle_scalars = particle.get_scalars();
    double current_time = model.get_current_time();
    double timestep = model.get_timestep();

    double Dp = particle.get_equivalent_diameter();
    double3 velocity_p = particle.get_translational_velocity();

    if (data->activate_sensor[particle.get_particle_group_index()])
    {
        for(int i = 0; i < data->n_list_itens; i++)
        {
            const bool& inside_roi = particle_scalars.get_scalar<bool>(data->ROI_index[i]);
            if (inside_roi && data->flag_start[i]==0)
            {
                data->flag_start[i] = 1;
                data->start_time_with_delay[i] = model.get_current_time() + data->activate_delay_time;
                data->final_time_with_delay[i] = model.get_current_time() + data->activate_delay_time + data->activate_total_time;
            }

            if (current_time + timestep > data->final_time_with_delay[i] && data->flag_start[i]==1)
            {
                data->flag_start[i] = 0;
            }
        }
    }

    for (int i = 0; i < data->n_list_itens; i++)
    {
        if (model.get_current_time() >= data->start_time_with_delay[i] && model.get_current_time() < data->final_time_with_delay[i])
        {
            auto pc = model.get_particle_cloud_point(data->pointcloud_index[i], particle);
            double3 velocity_f = {
                pc.get_property(data->u_index[i]),
                pc.get_property(data->v_index[i]),
                pc.get_property(data->w_index[i])};
            double3 velocity_r  =  velocity_f - velocity_p;
            
            double3 point_position = pc.get_position();
            double3 particle_position = particle.get_centroid_position();
            double distance = get_norm(point_position-particle_position);

            if (distance < data->distance_multiplier*Dp)
            {
                double3 drag_force = {
                    calculate_drag_force(data->fluid_density, data->fluid_viscosity, Dp, velocity_r.x),
                    calculate_drag_force(data->fluid_density, data->fluid_viscosity, Dp, velocity_r.y),
                    calculate_drag_force(data->fluid_density, data->fluid_viscosity, Dp, velocity_r.z)};
                drag_force *= data->factor;

                double norm_drag_force = get_norm(drag_force);
                particle_scalars.set_scalar(data->particle_scalar_index, norm_drag_force);
                particle.add_force(drag_force);
            }
            else 
            {
                particle_scalars.set_scalar(data->particle_scalar_index, 0.0);
            }
        }
        else 
        {
            particle_scalars.set_scalar(data->particle_scalar_index, 0.0);
        }
    }

}
ROCKY_PLUGIN_POST_FORCE_ON_PARTICLES_END()

ROCKY_PLUGIN_END
