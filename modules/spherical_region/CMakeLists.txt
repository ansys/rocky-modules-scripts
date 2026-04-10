find_package(RockySDK REQUIRED)

## PKG_NAME: Define name of custom module 
set(PKG_NAME "spherical_region")

## ROCKY_PLUGIN_INSTALLATION_DIR: Defines the installation folder.
# By default, the modules are installed in your ROCKY_PLUGINS_PATH 
# directory. If you want to change the installation folder for any
# reason, uncomment the line below and define your custom instalation path
#set(ROCKY_PLUGIN_INSTALLATION_DIR ${CMAKE_CURRENT_SOURCE_DIR}/custom_instalation_path/)

## Build module
add_library(${PKG_NAME} SHARED ${PKG_NAME}.cu)
target_link_libraries(${PKG_NAME} ${RockySDK_LIBRARIES})

## ASSETS_LIST: List the assets to be included. (.plugin and .py are mandatory)
set(ASSETS_LIST "${PKG_NAME}.plugin" "${PKG_NAME}.py" "${PKG_NAME}.pdf")

##Installing rocky plugin
install_rocky_plugin(${PKG_NAME} ASSETS_LIST)
