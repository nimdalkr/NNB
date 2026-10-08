#include <Windows.h>
#include <BWAPI.h>
#include <cstdio>
#include <filesystem>
#include <stdexcept>

// Verifies only loading and the module factory. No game process or onStart call.
int wmain(int argc,wchar_t** argv) {
  try {
    if(argc!=2)throw std::runtime_error("Provide a local NNB DLL");
    auto path=std::filesystem::absolute(argv[1]);
    auto library=LoadLibraryExW(path.c_str(),nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if(!library)throw std::runtime_error("LoadLibrary failed");
    auto init=reinterpret_cast<void (*)(BWAPI::Game*)>(GetProcAddress(library,"gameInit"));
    auto create=reinterpret_cast<BWAPI::AIModule* (*)()>(GetProcAddress(library,"newAIModule"));
    if(!init || !create)throw std::runtime_error("Missing AIModule exports");
    init(nullptr);auto bot=create();if(!bot)throw std::runtime_error("Factory returned null");
    delete bot;init(nullptr);FreeLibrary(library);
    std::puts("NNB x86: DLL load, factory and destruction passed. Gameplay not tested.");
    return 0;
  } catch(const std::exception& error){std::fprintf(stderr,"FAILED: %s\n",error.what());return 1;}
}
