/** @type {import("dependency-cruiser").IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "no-electron-imports-from-renderer-or-shared",
      comment: "A3: renderer/shared code must use window.bridge instead of importing Electron.",
      severity: "error",
      from: {
        path: "^src/(renderer|shared)/",
      },
      to: {
        path: "^electron$",
      },
    },
  ],
  options: {
    doNotFollow: {
      path: "node_modules",
    },
    tsPreCompilationDeps: true,
    tsConfig: {
      fileName: "tsconfig.json",
    },
  },
};
