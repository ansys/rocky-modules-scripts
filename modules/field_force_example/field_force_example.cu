
/*
Enables you to specify the name of the Point Cloud that was already defined with an imported force 
field .txt file, which will then be used as an additional body force acting on particles.
It can be used as an example of API: Solver usage.

This module expects the following three additional columns in the point cloud file: 'fx', 'fy' and 'fz'.
Besides that, it is mandatory to have columns representing each of the three cartesian coordinates: 'x', 'y' and 'z'.
*/

#define ROCKY_CUDA_API
#include <rocky20/api/rocky_api.h>
#include <rocky20/api/device/api_backend.hpp>

struct Data
{
    char point_cloud_name[64];

    int point_cloud_index{ -1 };
    int fx_index{ -1 }, fy_index{ -1 }, fz_index{ -1 };
};

ROCKY_PLUGIN("Field Force", "1.0.0")

ROCKY_PLUGIN_CONFIGURE(input_data, data)
{
    Data *plugin_data = new Data();

    auto name = input_data.get_model().get_string("point_cloud");
    memcpy(plugin_data->point_cloud_name, name.c_str(), name.size());

    ROCKY_MESSAGE_LOG("Phony Field Forces\nPoint Cloud: " << name)

    data = static_cast<void *>(plugin_data);
}

ROCKY_PLUGIN_SETUP(model, _data)
{
    auto data = static_cast<Data*>(_data);
    data->point_cloud_index = model.find_point_cloud(data->point_cloud_name);
    data->fx_index = model.find_point_cloud_property(data->point_cloud_index, "fx");
    data->fy_index = model.find_point_cloud_property(data->point_cloud_index, "fy");
    data->fz_index = model.find_point_cloud_property(data->point_cloud_index, "fz");
}

ROCKY_PLUGIN_NON_DIMENSIONALIZE(model, _data)
{
    auto data = static_cast<Data *>(_data);

    model.set_point_cloud_property_dimension(
        data->point_cloud_index, data->fx_index, model.get_force_factor());
    model.set_point_cloud_property_dimension(
        data->point_cloud_index, data->fz_index, model.get_force_factor());
    model.set_point_cloud_property_dimension(
        data->point_cloud_index, data->fy_index, model.get_force_factor());
}

ROCKY_PLUGIN_INITIALIZE(model, _data)
{
}

ROCKY_PLUGIN_TEAR_DOWN(model, data)
{
}

ROCKY_PLUGIN_INITIALIZE_CUDA(model, host_data, device_id, _device_data)
{
    Data *device_data = nullptr;
    CUDA_MALLOC_TYPE(device_data, 1, Data);
    CUDA_COPY_H2D(device_data, static_cast<Data *>(host_data), 1);
    _device_data = static_cast<void *>(device_data);
}

ROCKY_PLUGIN_TEAR_DOWN_CUDA(model, device_id, device_data)
{
    auto d_data = static_cast<Data*>(device_data);
    CUDA_FREE(d_data);
}

// Force -------------------------------------------------------------------------------------------
ROCKY_PLUGIN_POST_FORCE_ON_PARTICLES(model, particle, _data)
{
    auto data = static_cast<Data *>(_data);
    auto pc = model.get_particle_cloud_point(data->point_cloud_index, particle);

    double3 force = { pc.get_property(data->fx_index),
                      pc.get_property(data->fy_index),
                      pc.get_property(data->fz_index) };

    particle.add_force(force);
}
ROCKY_PLUGIN_POST_FORCE_ON_PARTICLES_END()

ROCKY_PLUGIN_END
