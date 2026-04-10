
/*
Enables you to define a spherical region and then mark 
particles inside of this region for later analysis.
It can be used as an example of API: Solver usage.
*/

/* Rocky API definitions and import header files */
#define ROCKY_CUDA_API
#include <rocky20/api/rocky_api.h>

/* Structure with local module variables */
struct ModuleData
{
    double3 sphere_center;      //  center of spherical region
    double  sphere_radius;      //  radius of spherical region
    int     scalar_index;       //  index of new particle scalar
};

/* Define module name and version (same as the one in the *.plugin file)*/
ROCKY_PLUGIN("Spherical Region", "1.0.0")

/* Hook used to retrieve input parameter values entered via the Rocky UI 
(defined in the Python specification file)*/
ROCKY_PLUGIN_CONFIGURE(input_data, data)
{
    /* Allocate memory for module local variables */
    ModuleData* module_data = new ModuleData();

    /* Access Rocky data model to retrieve input parameter values */
    auto model_properties = input_data.get_model();
    module_data->sphere_center.x = model_properties.get_double("center_x");
    module_data->sphere_center.y = model_properties.get_double("center_y");
    module_data->sphere_center.z = model_properties.get_double("center_z");
    module_data->sphere_radius = model_properties.get_double("radius");

    /* Cast module structure pointer to a generic pointer for internal handling */ 
    data = static_cast<void *>(module_data);
}

/* Hook used to allocate resources for the module */
ROCKY_PLUGIN_SETUP(model, data)
{
    /* Cast data to local structure */
    ModuleData* module_data = static_cast<ModuleData*>(data);

    /* Add a new scalar variable to the particle scalar's pool */
    auto scalars = model.get_particle_scalars();
    module_data->scalar_index = scalars.add("Inside Sphere Flag", "-");
}

/* Hook used to nondimensionalize local variables */
ROCKY_PLUGIN_NON_DIMENSIONALIZE(model, data)
{
    /* Cast data to local structure */
    ModuleData* module_data = static_cast<ModuleData*>(data);

    /* Scale local variables by the corresponding factor */
    module_data->sphere_center.x /= model.get_length_factor();
    module_data->sphere_center.y /= model.get_length_factor();
    module_data->sphere_center.z /= model.get_length_factor();
    module_data->sphere_radius /= model.get_length_factor();
}

/* Hook used to initialize data on GPU (mandatory) */
ROCKY_PLUGIN_INITIALIZE_CUDA(model, host_data, device_id, device_data)
{
    auto h_data = static_cast<ModuleData*>(host_data);

    ModuleData* d_data = nullptr;
    CUDA_MALLOC_TYPE(d_data, 1, ModuleData);
    CUDA_COPY_H2D(d_data, h_data, 1);
    device_data = static_cast<void*>(d_data);
}

/* Hook used to add custom code in a loop over active particles */
/* after updating their position and velocity */
ROCKY_PLUGIN_POST_MOVE_PARTICLES(device_model, particle, data)
{
    /* Cast data to local structure */
    ModuleData* module_data = static_cast<ModuleData*>(data);

    /* Get particle scalars */
    auto scalars = particle.get_scalars();

    /* Get scalar index */
    int scalar_index = module_data->scalar_index;

    /* Get particle centroid */
    double3 position = particle.get_centroid_position();

    /* Calculate distance between the particle's centroid and the center of the spherical region */
    double distance = get_norm(position - module_data->sphere_center);

    /* If the distance is lower than the radius, mark the particle as inside the region */
    if (distance < module_data->sphere_radius)
        scalars.set_scalar(scalar_index, 1.0);
    else
        scalars.set_scalar(scalar_index, 0.0);
}
/* Finalize hook (mandatory) */
ROCKY_PLUGIN_POST_MOVE_PARTICLES_END()

/* Hook used to free memory allocated on CPU */
ROCKY_PLUGIN_TEAR_DOWN(model, data)
{
    /* Deallocate local structure */
    delete static_cast<ModuleData *>(data);
}

/* Hook used to free resources on GPU (mandatory) */
ROCKY_PLUGIN_TEAR_DOWN_CUDA(model, device_id, device_data)
{
    auto d_data = static_cast<ModuleData*>(device_data);
    CUDA_FREE(d_data);
}

/* Finalize module (mandatory) */
ROCKY_PLUGIN_END