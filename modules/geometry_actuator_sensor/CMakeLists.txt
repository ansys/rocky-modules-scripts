find_package(RockySDK REQUIRED)

set(PKG_NAME "geometry_actuator_sensor")

add_library(${PKG_NAME} SHARED ${PKG_NAME}.cu)
target_link_libraries(${PKG_NAME} ${RockySDK_LIBRARIES})

set(ASSETS_LIST "${PKG_NAME}.plugin" "${PKG_NAME}.py")

install_rocky_plugin(${PKG_NAME} ASSETS_LIST)