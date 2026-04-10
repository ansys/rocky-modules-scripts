
/*
Enables you to use a Transient Adhesive Force model that will increase over 
time the adhesive forces between particles and between particles and boundaries. 
It can be used as an example of API: Solver usage.

The Transient Adhesive Force model implemented in this module is a variation of 
the built-in Constant Adhesive Force model in Rocky, in which the adhesive force 
asymptotically approaches the value defined in that model.

For more information about Rocky's built-in Constant Adhesive Force model, 
refer to the Rocky DEM Technical Manual. 
*/

#define ROCKY_CUDA_API
#include <rocky20/api/rocky_api.h>
#include <math.h>

struct ModuleData
{
    // This defines the maximum influence distance in which the particle-particle and 
    // particle-boundary adhesive forces will be accounted. Range: [Positive values]
    double adhesive_distance;
    // The initial value of the adhesive force will be equal to the product of the 
    // value of this parameter and the particle weight. Range: [Positive values]
    double initial_force_fraction;
    // The final value of the adhesive force will be equal to the product of the 
    // value of this parameter and the particle weight. Range: [Positive values]
    double final_force_fraction;
    // This defines the time coefficient used to change asymptotically the 
    // force fraction between initial and final values. Range: [Positive values]
    double time_coefficient;
    // This defines the time you want particles to begin being influenced 
    // by the transient adhesive force. Range: [Positive values]
    double start_time;
};

ROCKY_PLUGIN("Transient Adhesive Force", "2.0.0")

ROCKY_PLUGIN_CONFIGURE(input_data, module_data)
{
    auto data = new ModuleData();
    
    auto model = input_data.get_model();

    data->adhesive_distance = model.get_double("adhesive_distance");
    data->initial_force_fraction = model.get_double("adhesive_initial_force_fraction");
    data->final_force_fraction = model.get_double("adhesive_final_force_fraction");
    data->time_coefficient = model.get_double("adhesive_time_coefficient");
    data->start_time = model.get_double("adhesion_start_time");

    module_data = static_cast<void *>(data);
}

ROCKY_PLUGIN_NON_DIMENSIONALIZE(model, module_data)
{
    auto data = static_cast<ModuleData *>(module_data);

    data->adhesive_distance /= model.get_length_factor();
    data->time_coefficient *= model.get_time_factor();
    data->start_time /= model.get_time_factor();
}

ROCKY_PLUGIN_TEAR_DOWN(model, module_data)
{
    ModuleData* data = static_cast<ModuleData *>(module_data);
    delete data;
}


ROCKY_PLUGIN_INITIALIZE(model, _data)
{
    auto data = static_cast<ModuleData *>(_data);
    auto adhesive_distance_data = model.get_interactions_data();

    int n_groups = adhesive_distance_data.get_number_particle_groups();

    double adhesive_distance = data->adhesive_distance;

    for (int i = 0; i < n_groups; i++)
    {
        auto size_min_i = adhesive_distance_data.get_particle_min_sieve_size(i);
        if (size_min_i > 0.0)
        {
            int m_index_i = adhesive_distance_data.get_particle_material_index(i);
            for (int j = i; j < n_groups; j++)
            {
                auto size_min_j = adhesive_distance_data.get_particle_min_sieve_size(j);
                if (size_min_j > 0.0)
                {
                    int m_index_j = adhesive_distance_data.get_particle_material_index(j);
                    model.set_adhesive_distance(m_index_i, m_index_j, adhesive_distance);
                }
            }
            for (int bm = 0; bm < adhesive_distance_data.get_number_geometry_materials(); ++bm)
            {
                int m_index_bm = adhesive_distance_data.get_geometry_material_index(bm);
                model.set_adhesive_distance(m_index_i, m_index_bm, adhesive_distance);
            }
        }
    }
}


ROCKY_PLUGIN_INITIALIZE_CUDA(model, host_data, device_id, _device_data)
{
    auto module_data = static_cast<ModuleData *>(host_data);

    ModuleData *data_for_device = nullptr;
    CUDA_MALLOC_TYPE(data_for_device, 1,ModuleData);
    CUDA_COPY_H2D(data_for_device, module_data, 1);
    _device_data = static_cast<void *>(data_for_device);
}


ROCKY_PLUGIN_TEAR_DOWN_CUDA(model, device_id, device_data)
{
    auto d_data = static_cast<ModuleData*>(device_data);
    CUDA_FREE(d_data);
}

ROCKY_PLUGIN_COMPUTE_CONTACT_ADHESIVE_FORCES(contact, output_data, _data)
{
    auto data = static_cast<ModuleData *>(_data);

    double current_time = contact.get_current_time();
    if (data->start_time <= current_time)
    {
        double exponential = exp(-data->time_coefficient*(current_time-data->start_time));
        double factor = data->final_force_fraction - (data->final_force_fraction - data->initial_force_fraction)*exponential;

        auto home_particle = contact.get_home_particle();
        double home_particle_mass = home_particle.get_mass();
        double gravity_acceleration = get_norm(home_particle.get_gravity());
        double adhesive_force = 0.0;

        if (contact.is_particle_particle_contact())
        {
            auto near_particle = contact.get_near_particle();
            double near_particle_mass = near_particle.get_mass();

            if (home_particle_mass > near_particle_mass){
                adhesive_force = factor * gravity_acceleration * near_particle_mass;
            }
            else {
                adhesive_force = factor * gravity_acceleration * home_particle_mass;
            }
        }
        else if (contact.is_particle_triangle_contact())
        {
            adhesive_force = factor * gravity_acceleration * home_particle_mass;
        }
        output_data.set_normal_force(-adhesive_force);
    }
}
ROCKY_PLUGIN_COMPUTE_CONTACT_ADHESIVE_FORCES_END()

ROCKY_PLUGIN_END