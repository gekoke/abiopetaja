{ config
, lib
, pkgs
, abiopetaja
, ...
}:
let
  inherit (lib) mkEnableOption mkOption;
  inherit (lib.types) nonEmptyListOf str bool;
  cfg = config.services.abiopetaja;
in
{
  options.services.abiopetaja = {
    enable = mkEnableOption "Abiopetaja service";
    domains = mkOption { type = nonEmptyListOf str; };
    provisionCertificates = mkOption { type = bool; default = true; };
  };

  config = lib.mkIf cfg.enable {
    networking.firewall.allowedTCPPorts = [
      80
      443
    ];

    services.nginx = {
      enable = true;
      resolver.ipv6 = false;
      recommendedProxySettings = true;
      recommendedTlsSettings = true;
      virtualHosts =
        let
          config = {
            root = "/var/www/abiopetaja";

            forceSSL = cfg.provisionCertificates;
            enableACME = cfg.provisionCertificates;

            locations = {
              "/" = {
                proxyPass = "http://127.0.0.1:8000";
                extraConfig = ''
                  add_header X-Frame-Options SAMEORIGIN;
                '';
              };
              "/static/" = {
                extraConfig = ''
                  add_header X-Frame-Options SAMEORIGIN;
                '';
              };
            };
          };
        in
        lib.genAttrs cfg.domains (_: config);
    };

    users = {
      groups = {
        www-data = { };
      };

      users = {
        nginx = {
          extraGroups = [ "www-data" ];
        };
        abiopetaja = {
          isNormalUser = true;
          createHome = true;
        };
      };
    };

    systemd = {
      tmpfiles.rules = [
        # Create `/var/www` directory.
        # Give owner (abiopetaja) and group (www-data) read+write permissions.
        # We set the first bit to `2`, which makes the
        # directory "sticky." That is, any files in the directory
        # will automatically inherit the directory's permissions.
        # This is necesarry so that files moved to the directory
        # using Django's `collectstatic` get the correct permissions.
        "d /var/www/abiopetaja 2775 abiopetaja www-data"
      ];

      services.abiopetaja = {
        wantedBy = [ "multi-user.target" ];
        serviceConfig = {
          User = "abiopetaja";
          ExecStart =
            let
              env = abiopetaja.dependencyEnv;
              activationScript = pkgs.writeShellScriptBin "activate" ''
                set -e

                SECRET_KEY_FILE="/home/abiopetaja/DJANGO_SECRET_KEY.txt"

                if [ ! -f "$SECRET_KEY_FILE" ]; then
                    PASSWORD=$(${pkgs.pwgen}/bin/pwgen -s 32 1)
                    echo "$PASSWORD" > "$SECRET_KEY_FILE"
                    echo "Generated a new Django secret key and saved it to $SECRET_KEY_FILE"
                else
                    echo "File $SECRET_KEY_FILE already exists."
                fi

                ${env}/bin/python -m manage collectstatic --no-input --clear
                ${env}/bin/python -m manage makemigrations --check
                ${env}/bin/python -m manage migrate
                ${env}/bin/gunicorn abiopetaja.wsgi:application
              '';
            in
            "${activationScript}/bin/activate";
        };
      };
    };

    security.acme = lib.mkIf cfg.provisionCertificates {
      acceptTerms = true;
      defaults.email = "gregor@grigorjan.net";
    };
  };
}
