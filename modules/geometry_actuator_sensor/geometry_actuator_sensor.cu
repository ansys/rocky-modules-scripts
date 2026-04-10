// Includes
#define ROCKY_CUDA_API
#include <rocky20/api/device/api_backend.hpp>
#include <rocky20/api/rocky_api.h>
#include <math.h>


static std::vector<std::string> roi_names;
static std::vector<std::string> geometry_names;

struct Data
{
    double3 relative_orientation_vector;

    int motion_type;
    double3 translational_velocity;
    double3 rotation_velocity;
    double activate_total_time;
    double activate_delay_time;

    bool* activate_sensor;

    int n_list_itens;
    int n_particle_groups;
    int* ROI_index;
    int* geometry_index;
    int* motion_flag_start_sent;
    double* start_time_with_delay;
};

ROCKY_PLUGIN("Geometry Actuator Sensor", "1.0.0")

ROCKY_PLUGIN_CONFIGURE(input_data, _data)
{
    Data *data = new Data();
    auto model = input_data.get_model();

    data->relative_orientation_vector.x = model.get_double("relative_orientation_vector_x");
    data->relative_orientation_vector.y = model.get_double("relative_orientation_vector_y");
    data->relative_orientation_vector.z = model.get_double("relative_orientation_vector_z");
    double orientation_vector_norm = get_norm(data->relative_orientation_vector);
    if (orientation_vector_norm < 0.99999 || orientation_vector_norm > 1.00001)
        ROCKY_RUNTIME_ERROR(
            "Orientation vector is not a unit vector: {" << data->relative_orientation_vector.x << ", " << data->relative_orientation_vector.y << ", " << data->relative_orientation_vector.z << "}");

    data->motion_type = model.get_int("motion_type");

    data->translational_velocity.x = model.get_double("translational_velocity") * data->relative_orientation_vector.x;
    data->translational_velocity.y = model.get_double("translational_velocity") * data->relative_orientation_vector.y;
    data->translational_velocity.z = model.get_double("translational_velocity") * data->relative_orientation_vector.z;

    data->rotation_velocity.x = model.get_double("rotation_velocity") * data->relative_orientation_vector.x;
    data->rotation_velocity.y = model.get_double("rotation_velocity") * data->relative_orientation_vector.y;
    data->rotation_velocity.z = model.get_double("rotation_velocity") * data->relative_orientation_vector.z;

    data->activate_total_time = model.get_double("activate_total_time");
    data->activate_delay_time = model.get_double("activate_delay_time");

    data->n_list_itens = model.get_list_size("sensor_geometry_list");
    data->ROI_index = new int[data->n_list_itens]();
    data->geometry_index = new int[data->n_list_itens]();
    data->motion_flag_start_sent = new int[data->n_list_itens]();
    data->start_time_with_delay = new double[data->n_list_itens]();

    for (int i = 0; i < data->n_list_itens; ++i)
    {
        auto item_data = model.get_list_item("sensor_geometry_list", i);

        std::string name1 = item_data.get_string("roi_name");
        roi_names.push_back(name1);

        std::string name2 = item_data.get_string("geometry_name");
        geometry_names.push_back(name2);
    }

    data->n_particle_groups = input_data.get_number_particle_groups();
    data->activate_sensor = new bool[data->n_particle_groups]();
    for (int i = 0; i < data->n_particle_groups; ++i)
    {
        auto particle_data = input_data.get_particle_group_data(i);
        data->activate_sensor[i] = particle_data.get_bool("activate_sensor");
    }

    _data = static_cast<void *>(data);
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

        for (int j = 0; j < model.get_number_of_geometries(); ++j)
        {
            if (model.get_geometry_name(j) == geometry_names[i].c_str())
            {
                data->geometry_index[i] = j;
            }
        }
    }
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

    d_data.geometry_index = nullptr;
    CUDA_MALLOC_TYPE(d_data.geometry_index, size2, int);
    CUDA_COPY_H2D(d_data.geometry_index, h_data->geometry_index, size2);

    d_data.motion_flag_start_sent = nullptr;
    CUDA_MALLOC_TYPE(d_data.motion_flag_start_sent, size2, int);
    CUDA_COPY_H2D(d_data.motion_flag_start_sent, h_data->motion_flag_start_sent, size2);

    d_data.start_time_with_delay = nullptr;
    CUDA_MALLOC_TYPE(d_data.start_time_with_delay, size2, double);
    CUDA_COPY_H2D(d_data.start_time_with_delay, h_data->start_time_with_delay, size2);

    Data *device_data = nullptr;
    CUDA_MALLOC_TYPE(device_data, 1,Data);
    CUDA_COPY_H2D(device_data, &d_data, 1);
    _device_data = static_cast<void *>(device_data);
}

ROCKY_PLUGIN_BEGIN_ITERATION_CUDA(model, host_data, device_id, device_data)
{
    auto* d_data = static_cast<Data*>(device_data);
    auto* h_data = static_cast<Data*>(host_data);
    Data temp;
    CUDA_COPY_D2H(&temp, d_data, 1);
    CUDA_COPY_D2H(h_data->motion_flag_start_sent, temp.motion_flag_start_sent, temp.n_list_itens);
    CUDA_COPY_D2H(h_data->start_time_with_delay, temp.start_time_with_delay, temp.n_list_itens);
}

ROCKY_PLUGIN_TEAR_DOWN_CUDA(model, device_id, device_data)
{
    auto d_data = static_cast<Data*>(device_data);
    Data data_ptrs;
    CUDA_COPY_D2H(&data_ptrs, d_data, 1);
    CUDA_FREE(data_ptrs.ROI_index);
    CUDA_FREE(data_ptrs.geometry_index);
    CUDA_FREE(data_ptrs.activate_sensor);
    CUDA_FREE(data_ptrs.motion_flag_start_sent);
    CUDA_FREE(data_ptrs.start_time_with_delay);
    CUDA_FREE(d_data);
}

ROCKY_PLUGIN_TEAR_DOWN(model, _data)
{
    Data* data = static_cast<Data *>(_data);
    if (data->ROI_index)
        delete[] data->ROI_index;
    if (data->geometry_index)
        delete[] data->geometry_index;
    if (data->activate_sensor)
        delete[] data->activate_sensor;
    if (data->motion_flag_start_sent)
        delete[] data->motion_flag_start_sent;
    if (data->start_time_with_delay)
        delete[] data->start_time_with_delay;
    delete data;
}

ROCKY_PLUGIN_NON_DIMENSIONALIZE(model, _data)
{
    Data* data = static_cast<Data *>(_data);

    data->translational_velocity /= model.get_length_factor() / model.get_time_factor();
    data->rotation_velocity /= 1 / model.get_time_factor();
    data->activate_total_time /= model.get_time_factor();
    data->activate_delay_time /= model.get_time_factor();
}

ROCKY_PLUGIN_COMPUTE_GEOMETRIES_MOTION(model, motion, _data)
{
    Data* data = static_cast<Data *>(_data);

    double current_time = model.get_current_time();
    double timestep = model.get_timestep();
    double3 new_displacement = {0,0,0};
    double3 new_angle_displacement = {0,0,0};
    double3 new_orientation_angle = {0,0,0};
    double3 new_position = {0,0,0};
    int n_geometries = motion.get_number_of_geometries();

    for (int i = 0; i < data->n_list_itens; i++)
    {
        for (int j = 0; j < n_geometries; j++)
        {
            auto geometry = motion.get_geometry(j);
            if (geometry.get_id() == data->geometry_index[i])
            {
                if (!geometry.has_linked_motion_frame())
                {
                    if (data->motion_flag_start_sent[i] == 1 && current_time > data->start_time_with_delay[i])
                    {
                        if (data->motion_type==0)
                        {
                            if (current_time <= data->start_time_with_delay[i] + data->activate_total_time/2)
                            {
                                new_displacement = data->translational_velocity * timestep;
                                new_position = geometry.get_position() + new_displacement;
                                geometry.set_translational_velocity(data->translational_velocity);
                                geometry.set_position(new_position);
                            } 
                            else if (current_time <= data->start_time_with_delay[i] + data->activate_total_time)
                            {
                                new_displacement = -data->translational_velocity * timestep;
                                new_position = geometry.get_position() + new_displacement;
                                geometry.set_translational_velocity(-data->translational_velocity);
                                geometry.set_position(new_position);
                            }
                        }
                        else
                        {
                            if (current_time <= data->start_time_with_delay[i] + data->activate_total_time/2)
                            {
                                new_angle_displacement = data->rotation_velocity * timestep * M_PI / 180;
                                new_orientation_angle = geometry.get_orientation_euler_angles() + new_angle_displacement;
                                geometry.set_orientation_angles(new_orientation_angle);
                                geometry.set_rotational_velocity(data->rotation_velocity*M_PI/180);

                            } 
                            else if (current_time <= data->start_time_with_delay[i] + data->activate_total_time)
                            {
                                new_angle_displacement = -data->rotation_velocity * timestep * M_PI / 180;
                                new_orientation_angle = geometry.get_orientation_euler_angles() + new_angle_displacement;
                                geometry.set_orientation_angles(new_orientation_angle);
                                geometry.set_rotational_velocity(-data->rotation_velocity*M_PI/180);
                            }
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
}

ROCKY_PLUGIN_POST_MOVE_PARTICLES(model, particle, _data)
{
    Data* data = static_cast<Data *>(_data);

    auto particle_scalars = particle.get_scalars();
    double current_time = model.get_current_time();
    double timestep = model.get_timestep();
    
    if (data->activate_sensor[particle.get_particle_group_index()])
    {
        for(int i = 0; i < data->n_list_itens; i++)
        {
            auto geometry_scalars = model.get_geometry_scalars(i);
            const bool& inside_roi = particle_scalars.get_scalar<bool>(data->ROI_index[i]);

            if (inside_roi && data->motion_flag_start_sent[i]==0)
            {
                data->motion_flag_start_sent[i] = 1;
                data->start_time_with_delay[i] = model.get_current_time() + data->activate_delay_time;
            }

            if (current_time + timestep > data->start_time_with_delay[i] + data->activate_total_time)
            {
                data->motion_flag_start_sent[i] = 0;
            }
        }
    }
}
ROCKY_PLUGIN_POST_MOVE_PARTICLES_END()

ROCKY_PLUGIN_END