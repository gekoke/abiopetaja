{ inputs, self, ... }:
{
  imports = [
    inputs.pre-commit-hooks.flakeModule
  ];

  perSystem = { pkgs, lib, system, ... }: {
    pre-commit =
      let
        pythonEnv = self.packages.${system}.default.dependencyEnv;
      in
      {
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
              entry = lib.mkForce "${pkgs.pyright}/bin/pyright --pythonpath ${pythonEnv}/bin/python";
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
              entry = "${pythonEnv}/bin/pytest";
              pass_filenames = false;
            };
          };
        };
      };
  };

  flake = {
    checks = builtins.mapAttrs (system: deployLib: deployLib.deployChecks self.deploy) inputs.deploy-rs.lib;
  };
}
