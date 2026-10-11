// Owns bounded Windows child-process crash diagnosis without masking failures.
#define NOMINMAX
#include <windows.h>
#include <dbghelp.h>
#include <chrono>
#include <iostream>
#include <string>

namespace {
std::wstring quote(const wchar_t *argument) {
  std::wstring result=L"\""; unsigned slashes=0;
  for (const wchar_t *p=argument; *p; ++p) {
    if (*p==L'\\') { ++slashes; continue; }
    result.append(*p==L'"' ? slashes*2+1 : slashes,L'\\');
    result+=*p; slashes=0;
  }
  result.append(slashes*2,L'\\'); return result+L'"';
}
void trace(HANDLE process, DWORD threadId, const EXCEPTION_RECORD &exception) {
  std::cerr<<"WINDOWS_EXCEPTION code=0x"<<std::hex<<exception.ExceptionCode
           <<" address="<<exception.ExceptionAddress<<std::dec<<'\n';
  for (DWORD i=0;i<exception.NumberParameters;++i)
    std::cerr<<"  exception_parameter["<<i<<"]=0x"<<std::hex<<exception.ExceptionInformation[i]<<std::dec<<'\n';
  SymRefreshModuleList(process);
  auto thread=OpenThread(THREAD_GET_CONTEXT|THREAD_QUERY_INFORMATION,FALSE,threadId);
  if (!thread) return;
  CONTEXT context{}; context.ContextFlags=CONTEXT_FULL;
  if (!GetThreadContext(thread,&context)) { CloseHandle(thread); return; }
  STACKFRAME64 frame{};
  frame.AddrPC={context.Rip,0,AddrModeFlat};
  frame.AddrStack={context.Rsp,0,AddrModeFlat};
  frame.AddrFrame={context.Rbp,0,AddrModeFlat};
  for (unsigned i=0;i<32 && frame.AddrPC.Offset;++i) {
    IMAGEHLP_MODULE64 module{};module.SizeOfStruct=sizeof(module);
    if (SymGetModuleInfo64(process,frame.AddrPC.Offset,&module))
      std::cerr<<"  "<<(module.ImageName[0] ? module.ImageName : module.ModuleName)<<"+0x"<<std::hex<<(frame.AddrPC.Offset-module.BaseOfImage)<<std::dec;
    else std::cerr<<"  0x"<<std::hex<<frame.AddrPC.Offset<<std::dec;
    alignas(SYMBOL_INFO) unsigned char storage[sizeof(SYMBOL_INFO)+MAX_SYM_NAME]{};
    auto symbol=reinterpret_cast<SYMBOL_INFO*>(storage);
    symbol->SizeOfStruct=sizeof(SYMBOL_INFO);symbol->MaxNameLen=MAX_SYM_NAME;
    DWORD64 displacement{};
    if (SymFromAddr(process,frame.AddrPC.Offset,&displacement,symbol))
      std::cerr<<" "<<symbol->Name<<"+0x"<<std::hex<<displacement<<std::dec;
    std::cerr<<'\n';
    if (!StackWalk64(IMAGE_FILE_MACHINE_AMD64,process,thread,&frame,&context,nullptr,
                     SymFunctionTableAccess64,SymGetModuleBase64,nullptr)) break;
  }
  CloseHandle(thread);
}
}
int wmain(int argc,wchar_t **argv) {
  if (argc<2) { std::cerr<<"Usage: windows-process-probe executable [arguments]\n";return 2; }
  std::wstring command;
  for (int i=1;i<argc;++i) { if(i>1)command+=L' ';command+=quote(argv[i]); }
  STARTUPINFOW startup{};startup.cb=sizeof(startup);PROCESS_INFORMATION process{};
  if (!CreateProcessW(nullptr,command.data(),nullptr,nullptr,TRUE,DEBUG_ONLY_THIS_PROCESS,
                      nullptr,nullptr,&startup,&process)) {
    std::cerr<<"CreateProcess failed: "<<GetLastError()<<'\n';return 2;
  }
  SymSetOptions(SYMOPT_DEFERRED_LOADS|SYMOPT_UNDNAME);
  SymInitialize(process.hProcess,nullptr,TRUE);
  const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(90);
  DWORD result=2;bool exited=false,loaderBreakpoint=false;
  while(std::chrono::steady_clock::now()<deadline) {
    DEBUG_EVENT event{};
    if (!WaitForDebugEvent(&event,1000)) continue;
    DWORD disposition=DBG_CONTINUE;
    if(event.dwDebugEventCode==EXCEPTION_DEBUG_EVENT) {
      const auto &information=event.u.Exception;
      if(information.ExceptionRecord.ExceptionCode!=EXCEPTION_BREAKPOINT || loaderBreakpoint || !information.dwFirstChance) {
        disposition=DBG_EXCEPTION_NOT_HANDLED;
        if(!information.dwFirstChance) trace(process.hProcess,event.dwThreadId,information.ExceptionRecord);
      } else loaderBreakpoint=true;
    } else if(event.dwDebugEventCode==LOAD_DLL_DEBUG_EVENT && event.u.LoadDll.hFile)
      CloseHandle(event.u.LoadDll.hFile);
    else if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT && event.u.CreateProcessInfo.hFile)
      CloseHandle(event.u.CreateProcessInfo.hFile);
    else if(event.dwDebugEventCode==EXIT_PROCESS_DEBUG_EVENT) {
      result=event.u.ExitProcess.dwExitCode;exited=true;
    }
    ContinueDebugEvent(event.dwProcessId,event.dwThreadId,disposition);
    if(exited)break;
  }
  if(!exited) { std::cerr<<"Windows child probe timed out\n";TerminateProcess(process.hProcess,2); }
  SymCleanup(process.hProcess);CloseHandle(process.hThread);CloseHandle(process.hProcess);
  std::cerr<<"WINDOWS_CHILD_EXIT=0x"<<std::hex<<result<<std::dec<<'\n';
  return static_cast<int>(result);
}
