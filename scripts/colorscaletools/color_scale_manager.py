from barril.units import FixedArray
from plugins10core.pluginmanager import PluginManager
from sci20.plugins.grid_function.provider._grid_function_user_data_povider_ep import EPGridFunctionUserDataProvider
from sci20.app.grid_function._limits_options_interface import ILimitsOptions
from sci20.plugins.grid_function.provider.constants import SCOPE_GLOBAL
from coilib50.element_function.semantic_association import SemanticAssociation


class ColorScaleManager():
    """
    Responsible for handling the color scale
    """

    def __init__(self, app):
        self.process = app.GetStudy().GetParticles().GetSubject()
        self.provider = PluginManager.GetSingleton(
            EPGridFunctionUserDataProvider)
        self.gf_data = None

    def set_process(self, process):
        """Sets the process
        """
        self.process = process

    def set_gf_semantic_association_and_data(self, gf_name: str, app):
        """Sets the grid function semantic association

        Args:
            gf_name (str): grid function name
            app (_type_): application
        """
        if gf_name == "Velocity":
            self.semantic_association = SemanticAssociation(
                group_type='vectorial', unknown_data='Velocity', vector_property='magnitude')
        else:
            self.semantic_association = app._GetGridFunctionAssociation(
                self.process, gf_name, [])

        self.gf_data = self.provider.ObtainGridFunctionUserDataInScope(
            self.semantic_association, SCOPE_GLOBAL)

    def set_ticks_count(self, ticks_count: int):
        """Sets the color scale number of ticks

        Args:
            ticks_count (int): number of ticks
        """
        self.gf_data.color_scale.ticks_count = ticks_count

    def set_custom_limits(self, limits: list, unit_type: str, unit: str):
        """Sets color scale limits

        Args:
            limits (list): lower and upper limits
            unit_type (str): _description_
            unit (str): unit
        """
        self.gf_data.limits_option = ILimitsOptions.OPTION_CUSTOM
        self.gf_data.limits_custom = FixedArray(2, unit_type, limits, unit)

    def set_preferred_units(self, unit: str):
        """Sets the color scale preferred units

        Args:
            unit (str): unit
        """
        self.gf_data.limits_preferred_unit = unit

    def set_colors(self, colors: tuple):
        """Sets the color scale positions and colors

        Args:
            colors (tuple): colors used

        Raises:
            TypeError: If non grid function data is available
        """
        if self.gf_data is not None:
            try:
                self.gf_data.color_scale.SetMarkPositionsAndColors(
                    colors
                )
            except:
                pass
        else:
            raise TypeError("Grid Function Data cannot be None")
