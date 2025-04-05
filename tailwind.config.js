/** @type {import('tailwindcss').Config} */

module.exports = {
  content: ["./templates/**/*.html", "./**/templates/**/*.html"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: '#191645',
      },
    },
  },
  plugins: [require("flowbite/plugin"), require("flowbite-typography")],
};
