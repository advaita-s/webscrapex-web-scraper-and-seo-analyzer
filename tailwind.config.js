module.exports = {
  content: ["./pages/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brandPurpleStart: "#7d3c98",
        brandPurpleEnd: "#141025",
        brandTeal: "#12c2a1"
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(180deg, #7d3c98 0%, #3b1f3e 40%, #0f0a18 100%)'
      }
    },
  },
  plugins: [],
}
