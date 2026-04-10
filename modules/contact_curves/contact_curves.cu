
/*
Enables Rocky to create additional Contact Frequency and Contact Number curves for both Geometries and Particles.
It can be used as an example of API: Solver usage.

Both curves are related to the contact, which is defined as a specific location that a particle has experienced a collision.
'Contact Number' computes the total of particle-particle or particle-boundary contacts that occurred 
during an interval between two consecutive output times. 
'Contact Frequency' computes the ratio between the total of particle-particle or particle-boundary contacts 
that occurred during an interval between two consecutive output times and the output interval itself.
*/

#define ROCKY_CUDA_API
#include <rocky20/api/rocky_api.h>
#include <rocky20/api/device/api_backend.hpp>

struct ModuleData
{
    double previous_time;
    int output_particles_contacts { 0 };
    int* output_geometry_contacts { nullptr };
};

ROCKY_PLUGIN("Contact Curves", "1.0.0")

ROCKY_PLUGIN_CONFIGURE(input_data, data)
{
    data = static_cast<void *>(new ModuleData());
}

ROCKY_PLUGIN_SETUP(model, _data)
{
    auto curve_collections = model.get_curve_collections();
    curve_collections.create_particles_time_curve("Contacts Number", "-");
    curve_collections.create_particles_time_curve("Contacts Frequency", "1/s");
    for (int i = 0; i < model.get_number_of_geometries(); i++)
    {
        curve_collections.create_geometry_time_curve(i, "Contacts Number", "-");
        curve_collections.create_geometry_time_curve(i, "Contacts Frequency", "1/s");
    }
}

ROCKY_PLUGIN_INITIALIZE(model, _data)
{
    auto data = static_cast<ModuleData*>(_data);
    data->output_geometry_contacts = new int[model.get_number_of_geometries()]();
}

ROCKY_PLUGIN_NON_DIMENSIONALIZE(model, _data)
{
    auto curve_collections = model.get_curve_collections();
    curve_collections.setup_particles_time_curve_dimension("Contacts Frequency", 1/model.get_time_factor());
    for (int i = 0; i < model.get_number_of_geometries(); i++)
    {
        curve_collections.setup_geometry_time_curve_dimension(i, "Contacts Frequency", 1/model.get_time_factor());
    }
}

ROCKY_PLUGIN_TEAR_DOWN(model, data)
{
    auto _data = static_cast<ModuleData*>(data);

    delete[] _data->output_geometry_contacts;
    delete _data;
}

ROCKY_PLUGIN_INITIALIZE_CUDA(model, host_data, device_id, _device_data)
{
   ModuleData tmp_data{}, *device_data = nullptr;

   const int num_geometries = model.get_number_of_geometries();
   CUDA_MALLOC_TYPE(tmp_data.output_geometry_contacts, num_geometries, int);
   CUDA_MEMSET(tmp_data.output_geometry_contacts, 0, num_geometries);
   CUDA_MALLOC_TYPE(device_data, 1, ModuleData);
   CUDA_COPY_H2D(device_data, &tmp_data, 1);

   _device_data = static_cast<void *>(device_data);
}

// Count contacts ==================================================================================

ROCKY_PLUGIN_POST_FORCE_ON_CONTACTS(model, contact, data)
{
    if (contact.just_started_frictional())
    {
        auto _data = static_cast<ModuleData*>(data);
        if (contact.is_particle_triangle_contact())
        {
            int geometry_id = contact.get_near_triangle().get_geometry_index();
            backend::atomic_add(&_data->output_geometry_contacts[geometry_id], 1);
        }
        else
        {
            backend::atomic_add(&_data->output_particles_contacts, 1);
        }
    }
}
ROCKY_PLUGIN_POST_FORCE_ON_CONTACTS_END()

// Sync data from gpu ==============================================================================

ROCKY_PLUGIN_PRE_OUTPUT_CUDA_SYNC_DATA(model, host_data, device_id, device_data)
{
   ModuleData tmp_data{};
   ModuleData *_data = static_cast<ModuleData*>(host_data);
   const int num_geometries = model.get_number_of_geometries();

   CUDA_COPY_D2H(&tmp_data, static_cast<ModuleData*>(device_data), 1);
   CUDA_COPY_D2H(_data->output_geometry_contacts, tmp_data.output_geometry_contacts, num_geometries);
   _data->output_particles_contacts = tmp_data.output_particles_contacts;

   // reset partial counters on gpu
   tmp_data.output_particles_contacts = 0;
   CUDA_MEMSET(tmp_data.output_geometry_contacts, 0, num_geometries);
   CUDA_COPY_H2D(static_cast<ModuleData*>(device_data), &tmp_data, 1);
}

// Update Time Curves ==============================================================================

ROCKY_PLUGIN_PRE_OUTPUT(model, _data)
{
    auto data = static_cast<ModuleData*>(_data);
    double output_time = model.get_current_time() - data->previous_time;
    
    IRockyCurveCollectionData curve_collections = model.get_curve_collections();
    curve_collections.update_particles_time_curve("Contacts Number", data->output_particles_contacts);
    curve_collections.update_particles_time_curve("Contacts Frequency", data->output_particles_contacts / output_time);

    for (int i = 0; i < model.get_number_of_geometries(); i++)
    {
        curve_collections.update_geometry_time_curve(
            i, "Contacts Number", data->output_geometry_contacts[i]);
        curve_collections.update_geometry_time_curve(
            i, "Contacts Frequency", data->output_geometry_contacts[i] / output_time);
    }
}

// Reset CPU counters ==============================================================================

ROCKY_PLUGIN_POST_OUTPUT(model, _data)
{
    auto data = static_cast<ModuleData*>(_data);
    data->output_particles_contacts = 0;
    for (int i = 0; i < model.get_number_of_geometries(); i++)
        data->output_geometry_contacts[i] = 0;

    data->previous_time = model.get_current_time();
}

ROCKY_PLUGIN_END
