# Generate an open-source Kyna repository

`ky generate repo my-app` creates a fresh local Git repository with a runnable Kyna entry point, manifest, README, ignore rules and MIT license. `--template backend` selects the existing backend scaffold. Existing directories are never overwritten.

`ky generate repo my-app --github qentrah/my-app` additionally commits the generated files, creates a **public** GitHub repository and pushes it using the authenticated `gh` account. The organization/name is explicit; no account or owner is hardcoded. Git identity, Git and GitHub CLI authentication must already be configured. Without `--github`, the command performs no GitHub operation.

External programs receive argument vectors, never shell text. Invalid names/remotes fail before project creation. Failures preserve local files for inspection and retry. KPROJECT1001 identifies input/conflict errors, KPROJECT1002 identifies external tooling/authentication failures, and KPROJECT1003 identifies file writes; diagnostics retain `kyna.diagnostic/v1` and exit status 2.

For a complete native application, see [Kyna Music](https://github.com/qentrah/kyna-music), whose application behavior is written in Kyna and whose Qt adapter provides native audio and presentation. Its build command automatically checks source, builds the adapter, tests application behavior and stages portable desktop artifacts.

GUI applications can set their icon from Kyna using `guiIcon("assets/icon.png")`, or `gui.icon(...)` through the checked package wrapper. The image must be a readable local image or Qt resource. The icon API changes the running application's icon; distribution-specific bundle/launcher icons must also be included by the application's packaging recipe.
