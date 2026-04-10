#define ROCKY_CUDA_API

#include <rocky20/api/rocky_api.h>
#include <rocky20/api/rocky_api_sph.h>
#include <rocky20/api/device/api_backend.hpp>
#include <rocky20/api/sph/api_cuda_sph.hpp>

struct Data
{
    int turbulent_viscosity_index { -1 };
    double les_smagorinsky_constant;
    double les_distance_factor;
};

ROCKY_PLUGIN("SPH LES Turbulence Model", "1.0.0")
ROCKY_PLUGIN_SPH()

ROCKY_PLUGIN_CONFIGURE(input_data, module_data)
{
    ROCKY_MESSAGE_LOG("SPHModelAPIAddin: configure");
    Data* data = new Data();
    auto model_properties = input_data.get_model();
    data->les_smagorinsky_constant = model_properties.get_double("les_smagorinsky_constant");
    data->les_distance_factor = model_properties.get_double("les_distance_factor");
    module_data = static_cast<void*>(data);
}

ROCKY_PLUGIN_SETUP(model, _data)
{
    ROCKY_MESSAGE_LOG("SPHModelAPIAddin: setup");
    auto data = static_cast<Data*>(_data);

    auto sph_model = get_sph_model(model);
    auto sph_scalars = sph_model.get_sph_element_scalars();
    data->turbulent_viscosity_index = sph_scalars.add("Turbulent Viscosity", "m2/s");
    sph_scalars.set_operation(data->turbulent_viscosity_index, sphotReset, sphopPreForce);
    sph_scalars.set_operation(data->turbulent_viscosity_index, sphotSum, sphopPreForce);
    sph_scalars.set_operation(data->turbulent_viscosity_index, sphotUpdate, sphopPreForce);
    ROCKY_MESSAGE_LOG(
        "Added scalar " << data->turbulent_viscosity_index << " reset/sum/update point "
                        << sphopPreForce);
}

ROCKY_PLUGIN_INITIALIZE_CUDA(model, host_data, device_id, _device_data)
{
    ROCKY_INFO_LOG("SPHModelAPIAddin: initialize_cuda");
    Data* device_copy = nullptr;
    CUDA_MALLOC_TYPE(device_copy, 1, Data);
    CUDA_COPY_H2D(device_copy, static_cast<Data*>(host_data), 1);
    _device_data = static_cast<void*>(device_copy);
}

ROCKY_PLUGIN_PRE_FORCE_ON_SPH_ELEMENT_INTERACTIONS(device_model, sph_model, sph_interaction, _data)
{
    auto data = static_cast<Data*>(_data);

    // Density for interacting elements
    auto home_element = sph_interaction.get_home_element();
    auto near_element = sph_interaction.get_near_element();
    auto home_scalars = home_element.get_scalars();
    auto near_scalars = near_element.get_scalars();
    const float home_density = home_element.get_density();
    const float near_density = near_element.get_density();

    // Distance & velocity difference between elements
    const float3 d_diff = sph_interaction.calculate_elements_distance();
    const float3 v_diff = sph_interaction.calculate_elements_relative_velocity();
    float dd = get_norm(d_diff);

    // Calculating the filtered strain rate per Violeau & Issa (2007)
    const float kernel_derivative = sph_model.get_kernel_derivative(dd);
    dd = max(dd, sph_model.get_minimum_distance());
    const float d_strain_rate = -0.5f * sph_model.get_mass() * (home_density + near_density)
    / (home_density * near_density) * dot(v_diff) * kernel_derivative / dd;

    // Accumulating strain rate contributions on the turbulent viscosity scalar
    home_scalars.add_scalar(data->turbulent_viscosity_index, d_strain_rate);
    near_scalars.add_scalar(data->turbulent_viscosity_index, d_strain_rate);
}
ROCKY_PLUGIN_PRE_FORCE_ON_SPH_ELEMENT_INTERACTIONS_END()

ROCKY_PLUGIN_PRE_FORCE_ON_SPH_ELEMENTS(device_model, sph_model, sph_element, _data)
{
    auto data = static_cast<Data*>(_data);

    // Calculating turbulence coefficient
    float coeff = sph_model.get_les_smagorinsky_constant() * sph_model.get_les_distance_factor()
        * sph_model.get_initial_element_spacing();
    coeff *= coeff;
    coeff *= sph_model.get_fluid_density();

    // Updating element turbulent viscosity
    auto element_scalars = sph_element.get_scalars();
    element_scalars.set_scalar(
        data->turbulent_viscosity_index,
        coeff * sqrt(2.0f * element_scalars.get_scalar(data->turbulent_viscosity_index)));
}
ROCKY_PLUGIN_PRE_FORCE_ON_SPH_ELEMENTS_END()

ROCKY_PLUGIN_FORCE_ON_SPH_ELEMENT_INTERACTIONS(
    rocky_model, sph_model, sph_interaction, _data)
{
    const float mass = sph_model.get_mass();
    auto data = static_cast<Data*>(_data);

    // Interaction elements
    auto home_element = sph_interaction.get_home_element();
    auto near_element = sph_interaction.get_near_element();
    auto home_scalars = home_element.get_scalars();
    auto near_scalars = near_element.get_scalars();

    // Distance & relative velocity between elements in contact
    const float3 d_diff = sph_interaction.calculate_elements_distance();
    const float3 v_diff = sph_interaction.calculate_elements_relative_velocity();
    float dd = get_norm(d_diff);
    const float kernel_derivative = sph_model.get_kernel_derivative(dd);

    // Pressures to density ratio
    const float home_density = home_element.get_density();
    const float near_density = near_element.get_density();
    const float home_pres_dens = home_element.get_pressure() / (home_density * home_density);
    const float near_pres_dens = near_element.get_pressure() / (near_density * near_density);

    // Acceleration due to Pressure forces
    float acc = kernel_derivative * mass * (home_pres_dens + near_pres_dens);

    // Pressure force vector
    dd = max(dd, sph_model.get_minimum_distance());
    float3 acceleration = -acc * d_diff / dd;

    // Viscous terms + LES turbulent model
    float home_viscosity = sph_model.get_fluid_viscosity();
    float near_viscosity = sph_model.get_fluid_viscosity();
    if (!home_element.is_dem_coupled() && !near_element.is_dem_coupled())
    {
        home_viscosity += home_scalars.get_scalar(data->turbulent_viscosity_index);
        near_viscosity += near_scalars.get_scalar(data->turbulent_viscosity_index);
    }

    /* Morris et al. (1997) approximation for the viscous term */
    float viscosity_coefficient = mass * (home_viscosity + near_viscosity) * kernel_derivative
        / (home_density * near_density) / dd;
    acceleration += viscosity_coefficient * v_diff;

    // Setting accelerations
    sph_interaction.add_acceleration(acceleration);
}
ROCKY_PLUGIN_FORCE_ON_SPH_ELEMENT_INTERACTIONS_END()

ROCKY_PLUGIN_FORCE_ON_SPH_TRIANGLE_INTERACTIONS(
    rocky_model, sph_model, sph_interaction, data)
{
    auto home_element = sph_interaction.get_home_element();
    const float mass = sph_model.get_mass();

    /* Boundary forces on free SPH elements only
        Without adhesive interaction (Free Slip Boundary) */
    if (home_element.is_enabled() && !home_element.is_dem_coupled())
    {
        // Interaction distance and velocity
        const float distance = sph_interaction.get_distance_to_home();
        const float3 unit_vector = sph_interaction.get_unit_vector();
        const auto boundary_velocity = sph_interaction.get_boundary_velocity();

        // Normal Acceleration
        float force = 0.0f;
        float dd = sph_model.get_boundary_distance_normal_factor()
            * sph_model.get_initial_element_spacing() - distance;
        float vnorm = 0.0f;
        const float3 home_velocity = sph_interaction.get_home_element_velocity();
        if (dd > 0.0f)
        {
            // Elastic part
            force += sph_model.get_stiffness() * dd;

            // Dissipation
            vnorm = dot(unit_vector, home_velocity - boundary_velocity);
            force -= sph_model.get_damping_coefficient() * vnorm;
            force = max(0.0f, force);
        }

        // Setting forces
        sph_interaction.add_force(force * unit_vector);
    }
}
ROCKY_PLUGIN_FORCE_ON_SPH_TRIANGLE_INTERACTIONS_END()

ROCKY_PLUGIN_SPH_END()

ROCKY_PLUGIN_END