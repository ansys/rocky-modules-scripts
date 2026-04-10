// Includes
#define ROCKY_CUDA_API
#include <rocky20/api/device/api_backend.hpp>
#include <rocky20/api/rocky_api.h>
#include <math.h>

struct Data
{
    double motion_start_time;
    char geometry_name[64];
    double motion_force_limit;
    double3 translational_velocity;

    int geometry_index;
    double absolute_start_time;
    double absolute_start_time_reverse;
    bool flag_reverse_motion;
    bool flag_stop_motion;
};

ROCKY_PLUGIN("Compression Motion", "0.0.0")

ROCKY_PLUGIN_CONFIGURE(input_data, _data)
{
    Data *data = new Data();
    auto model = input_data.get_model();

    data->motion_start_time = model.get_double("motion_start_time");
    data->motion_force_limit = model.get_double("motion_force_limit");
    data->translational_velocity.x = model.get_double("translational_velocity_x");
    data->translational_velocity.y = model.get_double("translational_velocity_y");
    data->translational_velocity.z = model.get_double("translational_velocity_z");

    auto name = model.get_string("geometry_name");
    memcpy(data->geometry_name, name.c_str(), name.size());

    data->flag_reverse_motion = false;
    data->flag_stop_motion = false;

    _data = static_cast<void *>(data);
}

ROCKY_PLUGIN_INITIALIZE(model, _data)
{
    auto data = static_cast<Data*>(_data);

    for (int j = 0; j < model.get_number_of_geometries(); ++j)
    {
        if (model.get_geometry_name(j) == data->geometry_name)
        {
            data->geometry_index = j;
        }
    }
}

ROCKY_PLUGIN_INITIALIZE_CUDA(model, host_data, device_id, _device_data)
{
    auto h_data = static_cast<Data*>(host_data);
    auto d_data = *h_data;

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
    CUDA_FREE(d_data);
}

ROCKY_PLUGIN_TEAR_DOWN(model, _data)
{
    Data* data = static_cast<Data *>(_data);
    delete data;
}

ROCKY_PLUGIN_NON_DIMENSIONALIZE(model, _data)
{
    Data* data = static_cast<Data *>(_data);

    data->motion_start_time /= model.get_time_factor();
    data->motion_force_limit /= model.get_force_factor();
    data->translational_velocity /= model.get_length_factor() / model.get_time_factor();
}

ROCKY_PLUGIN_COMPUTE_GEOMETRIES_MOTION(model, motion, _data)
{
    Data* data = static_cast<Data *>(_data);

    double current_time = model.get_current_time();
    double timestep = model.get_timestep();
    double3 new_displacement = {0,0,0};
    double3 new_position = {0,0,0};
    int n_geometries = motion.get_number_of_geometries();

    for (int j = 0; j < n_geometries; j++)
    {
        auto geometry = motion.get_geometry(j);
        if (geometry.get_id() == data->geometry_index)
        {
            if (!geometry.has_linked_motion_frame())
            {
                if (current_time > data->motion_start_time)
                {
                    if (current_time <= data->motion_start_time + timestep)
                    {
                        data->absolute_start_time = current_time;
                    }
                    if (get_norm(geometry.get_force()) >= data->motion_force_limit)
                    {
                        data->flag_reverse_motion = true;
                        data->absolute_start_time_reverse = current_time;
                    }
                    if (data->flag_reverse_motion)
                    {
                        double time = data->absolute_start_time_reverse - data->absolute_start_time;
                        double time_reverse = current_time - data->absolute_start_time_reverse;
                        if (time <= time_reverse + 1E-15)
                            data->flag_stop_motion = true;
                    }

                    if (!data->flag_reverse_motion && !data->flag_stop_motion)
                    {
                        new_displacement = data->translational_velocity * timestep;
                        new_position = geometry.get_position() + new_displacement;
                        geometry.set_translational_velocity(data->translational_velocity);
                        geometry.set_position(new_position);
                    } 
                    else if (data->flag_reverse_motion && !data->flag_stop_motion) 
                    {
                        new_displacement = -data->translational_velocity * timestep;
                        new_position = geometry.get_position() + new_displacement;
                        geometry.set_translational_velocity(-data->translational_velocity);
                        geometry.set_position(new_position);
                    }
                    else
                    {
                        geometry.set_translational_velocity({0,0,0});
                        geometry.set_rotational_velocity({0,0,0});
                    }
                }
                else
                {
                    geometry.set_translational_velocity({0,0,0});
                    geometry.set_rotational_velocity({0,0,0});
                }
            }
            else
            {
                ROCKY_RUNTIME_ERROR("The geometry '" << geometry.get_name() << "' has a linked internal motion frame. Review your setup");
            }
        }
    }
}

ROCKY_PLUGIN_END