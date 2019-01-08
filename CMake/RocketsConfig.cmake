get_filename_component(Rockets_CMAKE_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)

include(CMakeFindDependencyMacro)
find_dependency(Threads)

if(NOT TARGET Rockets)
    include("${Rockets_CMAKE_DIR}/RocketsTargets.cmake")
endif()
