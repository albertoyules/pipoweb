import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// H.264 en un MP4 normal y corriente: es lo que traga LinkedIn sin
// recodificar y lo que abre cualquier reproductor.
Config.setCodec("h264");
