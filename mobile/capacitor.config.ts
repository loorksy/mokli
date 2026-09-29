import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "app.mokli.personal",
  appName: "Mokli",
  webDir: "../web/dist",
  server: {
    androidScheme: "https",
    cleartext: true,
  },
};

export default config;
