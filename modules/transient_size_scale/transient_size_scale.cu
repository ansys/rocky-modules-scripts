
/*
Enables you to use a Transient Size Scale to increase the particle 
volume and mass over the predefined time interval. 
It can be used as an example of API: Solver usage.

The Transient Size Scale module creates a linear ramp between the
initial size scale, which is 1, and the final size scale, which you define,
over a specified time interval. As the simulation evolves, the mass
and volume of the particles will be increased in the same proportion,
in order to keep their density constant.
*/

#define ROCKY_CUDA_API
#include <rocky20/api/rocky_api.h>
#include <rocky20/api/device/api_backend.hpp>

struct scale_parameters
{
    // This defines the final size scale to achieve for the particle set. 
    // The initial size scale will always be 1. Range: [Values larger than 1]
    double final_size_scale;
    // This defines the time interval to reach the final size scale. 
    // The initial time will be the release particle time.
    double total_time;
};

struct ModuleData
{
    // Number of particle groups. (Internal variable for the module.)
    int n_groups;
    scale_parameters *scale_parameter;
    // Initial Volume Index. (Internal variable for the module.)
    int initial_volume_index;
    int flag_release_time_index;
    // Particle release time Index. (Internal variable for the module.)
    int release_time_index;
};

ROCKY_PLUGIN("Transient Size Scale", "1.1.0")

ROCKY_PLUGIN_CONFIGURE(input_data, module_data)
{
    auto data = new ModuleData();
    auto model = input_data.get_model();
    
    data->n_groups = input_data.get_number_particle_groups();
    data->scale_parameter = new scale_parameters[data->n_groups];

    for (int i = 0; i < data->n_groups; ++i)
    {
        auto group_data = input_data.get_particle_group_data(i);
        auto &group = data->scale_parameter[i];
        group.final_size_scale = group_data.get_double("scale_final_size_scale");
        group.total_time = group_data.get_double("scale_total_time");
    }
    module_data = static_cast<void*>(data);
}

ROCKY_PLUGIN_SETUP(model, module_data)
{
    auto data = static_cast<ModuleData*>(module_data);

    auto particle_scalars = model.get_particle_scalars();
    data->initial_volume_index = particle_scalars.add("Initial Volume", "m3", false);
    data->flag_release_time_index = particle_scalars.add("Flag Release Time", "-", false);
    data->release_time_index = particle_scalars.add("Release Time", "s", false);

    particle_scalars.enable_mass_increment();
    particle_scalars.enable_volume_increment();
}

ROCKY_PLUGIN_NON_DIMENSIONALIZE(model, module_data)
{
    auto data = static_cast<ModuleData *>(module_data);

    double volume_factor = pow(model.get_length_factor(), 3);
    model.get_particle_scalars().set_dimension(data->initial_volume_index, volume_factor);
    model.get_particle_scalars().set_dimension(data->release_time_index, model.get_time_factor());

    for (int i = 0; i < data->n_groups; ++i)
    {
        auto &group = data->scale_parameter[i];
        group.total_time /= model.get_time_factor();
    }
}

ROCKY_PLUGIN_TEAR_DOWN(model, module_data)
{
    ModuleData* data = static_cast<ModuleData *>(module_data);
    if (data->scale_parameter)
        delete[] data->scale_parameter;
    delete data;
}

ROCKY_PLUGIN_INITIALIZE_CUDA(model, host_data, device_id, _device_data)
{
    auto h_data = static_cast<ModuleData *>(host_data);
    auto d_data = *h_data;

    scale_parameters* d_group_parameter = nullptr;
    int size = h_data->n_groups;
    CUDA_MALLOC_TYPE(d_group_parameter, size,scale_parameters);
    CUDA_COPY_H2D(d_group_parameter, h_data->scale_parameter, size);
    d_data.scale_parameter = d_group_parameter;

    ModuleData *device_data = nullptr;
    CUDA_MALLOC_TYPE(device_data, 1,ModuleData);
    CUDA_COPY_H2D(device_data, &d_data, 1);
    _device_data = static_cast<void *>(device_data);
}


ROCKY_PLUGIN_TEAR_DOWN_CUDA(model, device_id, device_data)
{
    auto d_data = static_cast<ModuleData*>(device_data);
    ModuleData data_ptrs;
    CUDA_COPY_D2H(&data_ptrs, d_data, 1);
    CUDA_FREE(data_ptrs.scale_parameter);
    CUDA_FREE(d_data);
}


ROCKY_PLUGIN_PRE_MOVE_PARTICLES(model, particle, module_data)
{
    auto data = static_cast<ModuleData *>(module_data);

    auto scalars = particle.get_scalars();    
    double current_time = model.get_current_time();
    int pgindex = particle.get_particle_group_index();
    double particle_volume = particle.get_volume();

    double flag_release_time = scalars.get_scalar(data->flag_release_time_index);
    if (flag_release_time < 1.0)
    {
        scalars.set_scalar(data->initial_volume_index, particle_volume);
        scalars.set_scalar(data->release_time_index, current_time);
        scalars.set_scalar(data->flag_release_time_index, 1.0);
    }

    auto &group = data->scale_parameter[pgindex];
    double release_time = scalars.get_scalar(data->release_time_index);
    double stop_time = release_time + group.total_time;
    if (current_time <= stop_time)
    {
        double size_scale_factor = (
            (current_time - release_time) * (group.final_size_scale - 1)/
            (stop_time - release_time) + 1);
        double volume_scale_factor = (
            size_scale_factor * size_scale_factor * size_scale_factor);

        double initial_volume = scalars.get_scalar(data->initial_volume_index);
        double current_volume = volume_scale_factor * initial_volume;
        double volume_increment = current_volume - initial_volume;

        auto material = particle.get_material();
        double particle_density = material.get_density();
        double mass_increment = particle_density * volume_increment;
        
        // This provides the increment mass in relation to the original mass of each individual whole particle or fragment. 
        // This can help you to visualize the amount of mass that was added to each particle over time.
        scalars.set_mass_increment(mass_increment);
        // This provides the increment volume in relation to the original volume of each individual whole particle or fragment. 
        // This can help you to visualize the amount of volume that was added to each particle over time.
        scalars.set_volume_increment(volume_increment);
    }
}
ROCKY_PLUGIN_PRE_MOVE_PARTICLES_END()


ROCKY_PLUGIN_END

