// Owns fresh repository scaffolding and explicit public GitHub publication.
#include "project_internals.hpp"
#include <fstream>
namespace kyna::cli {
namespace {
[[noreturn]] void fail(std::string message, std::string code, std::string help) {
  Diagnostic diagnostic{std::move(message),{},false,std::move(code)};
  diagnostic.category="project";diagnostic.help=std::move(help);throw KynaError(diagnostic);
}
void execute(const std::string &program,std::vector<std::string> args,const fs::path &cwd={}) {
  ProcessConfig config;config.program=program;config.args=std::move(args);config.workingDir=cwd;config.captureOutput=true;
  auto result=productionRuntimeCapabilities().processes->spawn(config);
  if(result.failedToStart||result.exitCode!=0)
    fail(program+" failed: "+(result.failedToStart?result.startError:result.stderrText),"KPROJECT1002",
         "Install git and GitHub CLI as needed; configure Git identity and run gh auth login. Generated local files are preserved.");
}
bool simple(std::string_view value) {
  return !value.empty()&&value.front()!='-'&&value!="."&&value!=".."&&
    value.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")==std::string_view::npos;
}
}
int generateRepository(const Options &options,std::ostream &output,std::ostream &errors) {
  if(!simple(options.generatorName))fail("Invalid repository directory name","KPROJECT1001","Use a simple name with letters, digits, dots, underscores or hyphens.");
  if(!options.githubRepository.empty()) {
    auto slash=options.githubRepository.find('/');
    if(slash==std::string::npos||!simple(options.githubRepository.substr(0,slash))||!simple(options.githubRepository.substr(slash+1)))
      fail("Invalid GitHub repository","KPROJECT1001","Use --github OWNER/REPO. This flag creates a PUBLIC repository and pushes the generated files.");
  }
  auto root=fs::absolute(options.generatorName);
  if(fs::exists(root))fail("Repository directory already exists","KPROJECT1001","Choose a new name. Existing directories are never overwritten or published.");
  execute("git",{"--version"});
  if(!options.githubRepository.empty())execute("gh",{"auth","status"});
  auto scaffold=options;scaffold.noGit=true;scaffold.quiet=true;
  if(!scaffoldProject(root,options.templateName.empty()?"minimal":options.templateName,scaffold,output,errors))return 2;
  std::string error;
  const auto readme="# "+options.generatorName+"\n\nBuilt with [Kyna](https://github.com/qentrah/Kyna).\n\n```sh\nky check\nky run\nky build --output build/app\n```\n\nSource: `src/main.kyna`. Edit `kyna.toml` to configure the project.\n";
  if(!projectWrite(root/"README.md",readme,error)||!projectWrite(root/"LICENSE",
    "MIT License\n\nCopyright (c) Project contributors\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the Software), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n",error))
    fail(error,"KPROJECT1003","Check directory permissions. Generated files are preserved.");
  execute("git",{"init","-b","main"},root);
  if(!options.githubRepository.empty()) {
    execute("git",{"add","--","."},root);
    execute("git",{"commit","-m","Create Kyna application"},root);
    execute("gh",{"repo","create",options.githubRepository,"--public","--source",root.string(),"--remote","origin","--push"},root);
    output<<"Published https://github.com/"<<options.githubRepository<<'\n';
  } else output<<"Created local repository "<<root.string()<<"\nRun ky check and ky run inside it.\n";
  return 0;
}
}
