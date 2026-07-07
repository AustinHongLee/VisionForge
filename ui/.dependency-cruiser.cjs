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
    {
      name: "no-renderer-imports-from-main-or-preload",
      comment: "D13: renderer code must not import Electron process code.",
      severity: "error",
      from: {
        path: "^src/renderer",
      },
      to: {
        path: "^src/(main|preload)",
      },
    },
    {
      name: "no-main-or-preload-imports-from-renderer",
      comment: "D13: Electron process code must not import renderer code.",
      severity: "error",
      from: {
        path: "^src/(main|preload)",
      },
      to: {
        path: "^src/renderer",
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
