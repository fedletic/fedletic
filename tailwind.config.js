/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./**/templates/**/*.{html,js}"
    ],
    theme: {
        extend: {
            colors: {
                'royal-purple': {
                    DEFAULT: '#6A1B9A',
                    dark: '#4A148C',
                    light: '#9C27B0',
                    lighter: '#CE93D8',
                },
                'vivid-amber': {
                    DEFAULT: '#FFC107',
                    dark: '#FFA000',
                    light: '#FFECB3',
                },
                'text': {
                    dark: '#263238',
                    medium: '#546E7A',
                    light: '#B0BEC5',
                },
                'primary-bg': '#121016',
            }
        },
    },
    plugins: [
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
    ],
}