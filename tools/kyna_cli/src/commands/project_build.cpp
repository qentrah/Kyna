// Owns explicit local native builds and Kyna application staging.
#include "project_internals.hpp"
#include <kyna/stdlib/sha256.hpp>
#include <fstream>
#include <sstream>
namespace kyna::cli {
namespace {
[[noreturn]] void buildFailure(std::string message, std::string code, std::string help) {
 Diagnostic diagnostic{std::move(message),{},false,std::move(code)};
 diagnostic.category="build";diagnostic.help=std::move(help);throw KynaError(diagnostic);
}
// Check resolved ownership, but preserve the authored path for module imports.
fs::path stagedSourcePath(const fs::path &file,const fs::path &root) {
 auto resolved=fs::weakly_canonical(file).lexically_relative(fs::weakly_canonical(root));
 if(resolved.empty()||resolved.is_absolute()||*resolved.begin()=="..")
  buildFailure("Application source escapes its package","KBUILD1002","Keep source symlinks inside their owning project or dependency");
 auto authored=file.lexically_relative(root);
 if(authored.empty()||authored.is_absolute()||*authored.begin()=="..")
  buildFailure("Invalid application source path","KBUILD1002","Keep source paths inside their owning package");
 return authored;
}
struct Staging {
 fs::path path;bool committed{false};
 ~Staging(){if(!committed){std::error_code error;fs::remove_all(path,error);}}
};
}

int buildProject(const Options &options,std::ostream &output,std::ostream &errors) try {
 auto root=discoverProject();if(root.empty())root=fs::current_path();auto destination=fs::absolute(options.buildOutput).lexically_normal();
 if(options.buildNative)return buildNativeProject(options,root,destination,output);
 std::string error;auto entry=options.input.empty()?projectEntry(root,error):fs::absolute(options.input);if(!error.empty())buildFailure(error,"KBUILD1003","Set project.entry in kyna.toml or supply an entry file");
 auto sessionOptions=makeSessionOptions(options);sessionOptions.modulePaths.push_back(root);LanguageSession session(std::move(sessionOptions));auto result=session.check(entry);if(!result.ok())return renderResult(result,options,session,errors);
 if(fs::exists(destination))buildFailure("Output directory already exists","KBUILD1001","Choose a fresh --output path");
 if(destination==root||root.string().starts_with(destination.string()+"/"))buildFailure("Output cannot contain the project","KBUILD1001","Choose a separate output directory");
 Staging staging{destination};
 fs::create_directories(destination/"app");fs::create_directories(destination/"bin");
 for(fs::recursive_directory_iterator it(root),end;it!=end;++it){auto name=it->path().filename().string();if(it->is_directory()&&(name==".git"||name=="node_modules"||name.starts_with("build")||it->path()==destination)){it.disable_recursion_pending();continue;}if(!it->is_regular_file())continue;auto ext=it->path().extension();if(ext!=".ky"&&ext!=".kyna"&&ext!=".toml"&&name!="native.lock"&&ext!=".native"&&ext!=".off"&&!fs::relative(it->path(),root).generic_string().starts_with(".kyna/native/"))continue;auto target=destination/"app"/stagedSourcePath(it->path(),root);fs::create_directories(target.parent_path());fs::copy_file(it->path(),target);}
 // Stage source dependencies and replace project-local lookup paths in the bundle.
 if(fs::exists(root/"kyna.toml")) {
  auto manifest=loadManifest(root,error);
  if(auto deps=manifest["dependencies"].as_table())for(auto &[name,node]:*deps){
   auto table=node.as_table();if(!table)continue;auto path=(*table)["path"].value<std::string>();auto git=(*table)["git"].value<std::string>();if(!path&&!git)continue;
   auto packageName=std::string(name.str());if(packageName.empty()||packageName.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")!=std::string::npos)buildFailure("Invalid dependency name","KBUILD1002","Use letters, digits, underscores, or hyphens for package names");
   auto source=fs::weakly_canonical(path?root / *path:cacheRoot()/"git"/packageName);auto package=fs::path(".kyna/packages")/std::string(name.str());auto target=destination/"app"/package;
   if(!fs::is_directory(source))buildFailure("Dependency source directory is missing","KBUILD1002","Run ky install before building the application");
   for(fs::recursive_directory_iterator it(source),end;it!=end;++it){auto name=it->path().filename().string();if(it->is_directory()&&(name==".git"||name=="node_modules"||name.starts_with("build")||it->path()==destination)){it.disable_recursion_pending();continue;}if(!it->is_regular_file())continue;auto ext=it->path().extension();if(ext!=".ky"&&ext!=".kyna")continue;auto file=target/stagedSourcePath(it->path(),source);fs::create_directories(file.parent_path());fs::copy_file(it->path(),file,fs::copy_options::overwrite_existing);}
   table->insert_or_assign("path",package.generic_string());
  }
  if(auto assets=manifest["build"]["assets"].node()) {
   auto list=assets->as_array();
   if(!list)buildFailure("build.assets must be an array of file paths","KBUILD1002","List local application assets explicitly in kyna.toml");
   for(const auto &asset:*list) {
    auto name=asset.value<std::string>();
    if(!name||name->empty())buildFailure("Invalid application asset","KBUILD1002","Each asset must name a file inside the project");
    auto path=fs::path(*name);
    if(path.has_root_path())buildFailure("Application asset must be relative","KBUILD1002","Use a path relative to kyna.toml");
    for(const auto &part:path)if(part=="..")buildFailure("Application asset escapes the project","KBUILD1002","Keep assets inside the project directory");
    auto source=fs::weakly_canonical(root/path);
    auto relative=fs::relative(source,fs::weakly_canonical(root));
    if(relative.empty()||relative.generic_string().starts_with("..")||!fs::is_regular_file(source))buildFailure("Application asset is missing or outside the project","KBUILD1002","Check the declared asset and avoid external symlinks");
    auto target=destination/"app"/path;
    fs::create_directories(target.parent_path());
    if(!fs::exists(target))fs::copy_file(source,target);
   }
  }
  if(!saveManifest(destination/"app",manifest,error))buildFailure(error,"KBUILD1003","Check output directory permissions");
 }
 auto relative=fs::relative(entry,root);if(relative.empty()||relative.generic_string().starts_with(".."))buildFailure("Entry must belong to project","KBUILD1001","Supply an entry file inside the project directory");
#if defined(_WIN32)
 auto executable="ky.exe";
#else
 auto executable="ky";
#endif
 fs::copy_file(options.executable,destination/"bin"/executable);
 stageApplicationRuntime(options.executable,destination);
 std::string nativeShell,nativeCmd;
 for(const auto &library:options.nativeLibraries){
  auto name=library.filename().string();
  if(name.empty()||name.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")!=std::string::npos)buildFailure("Invalid native library filename","KBUILD1002","Use a simple filename for explicitly supplied native libraries");
  auto target=destination/"bin/native"/name/name;fs::create_directories(target.parent_path());
  if(fs::exists(target))buildFailure("Duplicate native library filename","KBUILD1002","Give explicit native libraries distinct filenames");
  fs::copy_file(library,target);
  stageNativeRuntime(fs::absolute(library),target.parent_path());
  auto relativeLibrary="../bin/native/"+name+"/"+name;
  nativeShell+=" --native-library "+projectShellQuote(relativeLibrary);
  nativeCmd+=" --native-library \""+relativeLibrary+"\"";
 }

 std::string launcher="#!/bin/sh\nset -eu\ncd -- \"$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)/app\"\nexec ../bin/ky"+nativeShell+" run "+projectShellQuote(relative.generic_string())+" \"$@\"\n";
 if(!projectWrite(destination/"run",launcher,error))buildFailure(error,"KBUILD1003","Check output directory permissions");fs::permissions(destination/"run",fs::perms::owner_exec|fs::perms::group_exec|fs::perms::others_exec,fs::perm_options::add);
 if(!projectWrite(destination/"run.cmd","@echo off\r\ncd /d \"%~dp0app\"\r\n\"%~dp0bin\\ky.exe\""+nativeCmd+" run \""+relative.generic_string()+"\" %*\r\n",error))buildFailure(error,"KBUILD1003","Check output directory permissions");
 std::ostringstream sums;for(auto &item:fs::recursive_directory_iterator(destination)){if(!item.is_regular_file())continue;std::ifstream f(item.path(),std::ios::binary);std::ostringstream data;data<<f.rdbuf();sums<<detail::sha256Hex(data.str())<<"  "<<fs::relative(item.path(),destination).generic_string()<<'\n';}if(!projectWrite(destination/"SHA256SUMS",sums.str(),error))buildFailure(error,"KBUILD1003","Check output directory permissions");
 staging.committed=true;
 output<<"Built application: "<<destination.string()<<'\n';return 0;
}
catch(const fs::filesystem_error &error){buildFailure(error.what(),"KBUILD1003","Check paths and permissions; build into a fresh output directory");}
}
