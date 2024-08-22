{ inputs, self, ... }:
{
  imports = [
    inputs.pre-commit-hooks.flakeModule
  ];

  perSystem = { pkgs, lib, system, ... }:
    let
      pythonEnv = self.packages.${system}.abiopetaja-dev.dependencyEnv;
    in
    {
      checks = import ./tests { inherit self pkgs; };

      pre-commit = {
        settings = {
          hooks = {
            gitleaks = {
              enable = true;
              name = "gitleaks";
              entry = "${pkgs.gitleaks}/bin/gitleaks protect --verbose --redact --staged";
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
            djhtml = {
              enable = true;
              name = "djhtml";
              entry = "${pkgs.djhtml}/bin/djhtml abiopetaja app authentication common";
              pass_filenames = false;
            };
            djlint = {
              enable = true;
              name = "djlint";
              entry = "${pkgs.djlint}/bin/djlint --ignore 'H021,H030,H031' .";
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
