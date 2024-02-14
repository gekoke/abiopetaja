{ inputs, ... }:
{
  imports = [
    inputs.pre-commit-hooks.flakeModule
  ];

  perSystem = { pkgs, ... }: {
    pre-commit = {
      check.enable = true;

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
          };
          ruff = {
            enable = true;
          };
          ruff-formatting = {
            enable = true;
            name = "ruff-formatting";
            entry = "${pkgs.ruff}/bin/ruff format";
            pass_filenames = false;
          };
        };
      };
    };
  };
}
