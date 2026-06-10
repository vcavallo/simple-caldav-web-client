# Example NixOS module. Import from configuration.nix and set the options.
#
#   imports = [ ./caldav-web-client/deploy/nixos-module.nix ];
#   services.caldav-webclient = {
#     enable = true;
#     source = /var/lib/caldav-web-client;   # checkout containing backend/ and frontend/dist
#     configFile = "/run/secrets/caldav-config.yaml";
#     port = 8080;
#   };
{ config, lib, pkgs, ... }:

let
  cfg = config.services.caldav-webclient;
  python = pkgs.python311.withPackages (ps: with ps; [
    fastapi uvicorn caldav icalendar pyyaml pydantic python-dateutil
  ]);
in {
  options.services.caldav-webclient = {
    enable = lib.mkEnableOption "CalDAV web client";
    source = lib.mkOption {
      type = lib.types.path;
      description = "Path to the checkout (contains backend/ and frontend/dist).";
    };
    configFile = lib.mkOption {
      type = lib.types.str;
      description = "Path to config.yaml with calendar credentials.";
    };
    port = lib.mkOption {
      type = lib.types.port;
      default = 8080;
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services.caldav-webclient = {
      description = "CalDAV Web Client";
      after = [ "network.target" ];
      wantedBy = [ "multi-user.target" ];
      environment.CALDAV_CONFIG = cfg.configFile;
      serviceConfig = {
        WorkingDirectory = cfg.source;
        ExecStart = "${python}/bin/uvicorn backend.main:app --host 0.0.0.0 --port ${toString cfg.port}";
        Restart = "on-failure";
        DynamicUser = true;
      };
    };
  };
}
