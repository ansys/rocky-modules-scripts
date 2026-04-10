
/*
Enables you to define a translation or rotation motion 
to be applied to the gravity center of geometry.	
It can be used as an example of API: Solver usage.
*/

#define ROCKY_CUDA_API
#include <rocky20/api/rocky_api.h>
#include <math.h>

struct ModuleData
{
    double3 translational_velocity;
    double3 rotational_velocity;
    char motion_geometry_name[64];
    int motion_type;

    int geometry_index;
    int motion_frame_flag_index;
    double* motion_frame_flag_value;
};

ROCKY_PLUGIN("Motion Frame", "1.0.0")

ROCKY_PLUGIN_CONFIGURE(input_data, data)
{
    ModuleData* module_data = new ModuleData();

    auto model_properties = input_data.get_model();

    module_data->translational_velocity.x = model_properties.get_double("translational_velocity_x");
    module_data->translational_velocity.y = model_properties.get_double("translational_velocity_y");
    module_data->translational_velocity.z = model_properties.get_double("translational_velocity_z");

    module_data->rotational_velocity.x = model_properties.get_double("rotational_velocity_x");
    module_data->rotational_velocity.y = model_properties.get_double("rotational_velocity_y");
    module_data->rotational_velocity.z = model_properties.get_double("rotational_velocity_z");

    auto name = model_properties.get_string("geometry_name");
    memcpy(module_data->motion_geometry_name, name.c_str(), name.size());

    module_data->motion_type = model_properties.get_int("motion_type");


    data = static_cast<void *>(module_data);
}

ROCKY_PLUGIN_SETUP(model, data)
{
    ModuleData* module_data = static_cast<ModuleData*>(data);

    auto boundary_scalar = model.get_triangle_scalars();
    module_data->motion_frame_flag_index = boundary_scalar.add("Motion Frame Flag", "-");

    module_data->motion_frame_flag_value = new double[model.get_number_of_geometries()];

    for (int i = 0; i < model.get_number_of_geometries(); ++i)
    {
        if (module_data->motion_geometry_name == model.get_geometry_name(i)){
            module_data->motion_frame_flag_value[i] = 1.0;
            module_data->geometry_index = i;}
        else
            module_data->motion_frame_flag_value[i] = 0.0;
    }

    boundary_scalar.fill_with_geometry_values(module_data->motion_frame_flag_index, module_data->motion_frame_flag_value);
}

ROCKY_PLUGIN_NON_DIMENSIONALIZE(model, data)
{
    ModuleData* module_data = static_cast<ModuleData*>(data);

    module_data->translational_velocity.x /= model.get_length_factor() / model.get_time_factor();
    module_data->translational_velocity.y /= model.get_length_factor() / model.get_time_factor();
    module_data->translational_velocity.z /= model.get_length_factor() / model.get_time_factor();

    module_data->rotational_velocity.x /= 1 / model.get_time_factor();
    module_data->rotational_velocity.y /= 1 / model.get_time_factor();
    module_data->rotational_velocity.z /= 1 / model.get_time_factor();
}

ROCKY_PLUGIN_INITIALIZE_CUDA(model, host_data, device_id, _device_data)
{
    auto h_data = static_cast<ModuleData*>(host_data);
    auto d_data = *h_data;

    int size = model.get_number_of_geometries();
    d_data.motion_frame_flag_value = nullptr;
    CUDA_MALLOC_TYPE(d_data.motion_frame_flag_value, size, double);
    CUDA_COPY_H2D(d_data.motion_frame_flag_value, h_data->motion_frame_flag_value, size);

    ModuleData* device_data = nullptr;
    CUDA_MALLOC_TYPE(device_data, 1, ModuleData);
    CUDA_COPY_H2D(device_data, &d_data, 1);
    _device_data = static_cast<void*>(device_data);
}

ROCKY_PLUGIN_POST_MOVE_PARTICLES(device_model, particle, data)
{
    ModuleData* module_data = static_cast<ModuleData*>(data);
}
ROCKY_PLUGIN_POST_MOVE_PARTICLES_END()

ROCKY_PLUGIN_COMPUTE_GEOMETRIES_MOTION(model, motion, data)
{
    ModuleData* module_data = static_cast<ModuleData*>(data);
    double current_time = model.get_current_time();
    double timestep = model.get_timestep();
    int n_geometries = motion.get_number_of_geometries();
    double3 new_displacement = {0,0,0};
    double3 new_position = {0,0,0};
    double3 new_angle_displacement = {0,0,0};
    double3 new_orientation_angle = {0,0,0};

    for (int j = 0; j < n_geometries; j++)
    {
        auto geometry = motion.get_geometry(j);
        if (geometry.get_id() == module_data->geometry_index){
            if (!geometry.has_linked_motion_frame()){
                if (module_data->motion_type==0){
                    new_displacement = module_data->translational_velocity * timestep;
                    new_position = geometry.get_position() + new_displacement;
                    geometry.set_translational_velocity(module_data->translational_velocity);
                    geometry.set_position(new_position);
                }
                else{
                    new_angle_displacement = module_data->rotational_velocity * timestep * M_PI / 180;
                    new_orientation_angle = geometry.get_orientation_euler_angles() + new_angle_displacement;
                    geometry.set_orientation_angles(new_orientation_angle);
                    geometry.set_rotational_velocity(module_data->rotational_velocity*M_PI/180);
                }
            }
            else{
                ROCKY_RUNTIME_ERROR("The geometry '" << geometry.get_name() << "' has a linked internal motion frame. Review your setup");
            }
        }
    }
}

ROCKY_PLUGIN_TEAR_DOWN(model, data)
{
    ModuleData* module_data = static_cast<ModuleData*>(data);

    if (module_data->motion_frame_flag_value)
        delete[] module_data->motion_frame_flag_value;
    delete module_data;
}

ROCKY_PLUGIN_TEAR_DOWN_CUDA(model, device_id, device_data)
{
    auto d_data = static_cast<ModuleData*>(device_data);
    ModuleData data_ptrs;
    CUDA_COPY_D2H(&data_ptrs, d_data, 1);
    CUDA_FREE(data_ptrs.motion_frame_flag_value);
    CUDA_FREE(d_data);
}

ROCKY_PLUGIN_END