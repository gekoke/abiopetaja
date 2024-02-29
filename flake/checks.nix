{ inputs, ... }:
{
  imports = [
    inputs.pre-commit-hooks.flakeModule
  ];

  perSystem = { pkgs, lib, ... }: {
    pre-commit = {
      check.enable = false;

      settings = {
        hooks = {
          gitleaks = {
            enable = true;
            name = "gitleaks";
            entry = "${pkgs.gitleaks}/bin/gitleaks protect --verbose --redact --staged";
            pass_filenames = false;
          };
          pyright = {
            enable = true;
            entry = lib.mkForce "pyright --pythonversion 3.12";
            pass_filenames = false;
          };
          ruff = {
            enable = true;
            pass_filenames = false;
          };
          ruff-formatting = {
            enable = true;
            name = "ruff-formatting";
            entry = "${pkgs.ruff}/bin/ruff format";
            pass_filenames = false;
          };
          pytest = {
            enable = true;
            name = "pytest";
            entry = "pytest";
            pass_filenames = false;
          };
        };
      };
    };
  };
}
