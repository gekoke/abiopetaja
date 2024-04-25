{ inputs, self, ... }:
{
  imports = [
    inputs.pre-commit-hooks.flakeModule
  ];

  perSystem = { pkgs, lib, system, ... }: {
    checks = import ./tests { inherit self pkgs; };

    pre-commit =
      let
        pythonEnv = self.packages.${system}.abiopetaja-dev.dependencyEnv;
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
            makemessages =
              let
                makeMessages = pkgs.writeShellScriptBin "makemessages" ''
                  PATH=${pkgs.gettext}/bin:$PATH
                  ${pythonEnv}/bin/python -m django makemessages --all --no-obsolete --settings="abiopetaja.settings_dev"
                '';
              in
              {
                enable = true;
                name = "makemessages";
                entry = lib.getExe makeMessages;
                pass_filenames = false;
              };
            makemigrations = {
              enable = true;
              name = "makemigrations";
              entry = "${pythonEnv}/bin/python -m django makemigrations --check --settings='abiopetaja.settings_dev'";
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
