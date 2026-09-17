export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "scope-enum": [
      2,
      "always",
      [
        "identity",
        "work",
        "metrics",
        "integrations",
        "platform",
        "shared",
        "web",
        "api",
        "ci",
        "docs",
        "repo",
        "deps",
        "release",
      ],
    ],
    "subject-case": [2, "never", ["upper-case", "start-case", "pascal-case"]],
    "header-max-length": [2, "always", 100],
  },
};
