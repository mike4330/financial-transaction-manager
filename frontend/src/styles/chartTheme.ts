// Chart theme constants that match our Tailwind config
// These ensure consistent styling across all chart components

export const CHART_COLORS = {
  // Light mode colors
  light: {
    grid: '#e5e7eb',           // gray-200
    text: '#6b7280',           // gray-500  
    background: '#ffffff',     // white
    tooltipBg: '#ffffff',      // white
    tooltipBorder: '#d1d5db',  // gray-300
    axis: '#e5e7eb',          // gray-200
  },
  
  // Dark mode colors (from our Tailwind config)
  dark: {
    grid: '#3a2f20',           // dark-border
    text: '#a8a29e',           // warm-400
    background: '#252017',     // dark-card
    tooltipBg: '#2d251a',      // dark-elevated
    tooltipBorder: '#3a2f20',  // dark-border
    axis: '#3a2f20',          // dark-border
  },
  
  // Ember accent colors
  ember: {
    primary: '#ed7014',        // ember-500
    glow: 'rgba(237, 112, 20, 0.1)',     // ember-500 with 10% opacity
    glowStrong: 'rgba(237, 112, 20, 0.15)', // ember-500 with 15% opacity
    light: '#f29432',          // ember-400
    dark: '#de550a',           // ember-600
  }
};

// Chart theme generator function
export const getChartTheme = (isDarkMode: boolean) => ({
  gridColor: isDarkMode ? CHART_COLORS.dark.grid : CHART_COLORS.light.grid,
  textColor: isDarkMode ? CHART_COLORS.dark.text : CHART_COLORS.light.text,
  backgroundColor: isDarkMode ? CHART_COLORS.dark.background : CHART_COLORS.light.background,
  tooltipBg: isDarkMode ? CHART_COLORS.dark.tooltipBg : CHART_COLORS.light.tooltipBg,
  tooltipBorder: isDarkMode ? CHART_COLORS.dark.tooltipBorder : CHART_COLORS.light.tooltipBorder,
  axisColor: isDarkMode ? CHART_COLORS.dark.axis : CHART_COLORS.light.axis,
  emberGlow: CHART_COLORS.ember.glow,
  emberGlowStrong: CHART_COLORS.ember.glowStrong,
});

// Grid stroke properties for charts
export const getGridProps = (isDarkMode: boolean) => ({
  strokeDasharray: "3 3",
  stroke: isDarkMode ? CHART_COLORS.dark.grid : CHART_COLORS.light.grid,
  strokeOpacity: isDarkMode ? 0.8 : 0.5,
});

// Axis properties for charts
export const getAxisProps = (isDarkMode: boolean) => ({
  tick: { 
    fill: isDarkMode ? CHART_COLORS.dark.text : CHART_COLORS.light.text, 
    fontSize: 12 
  },
  axisLine: { 
    stroke: isDarkMode ? CHART_COLORS.dark.axis : CHART_COLORS.light.axis 
  },
  tickLine: { 
    stroke: isDarkMode ? CHART_COLORS.dark.axis : CHART_COLORS.light.axis 
  },
});

// Tooltip styling properties
export const getTooltipProps = (isDarkMode: boolean) => ({
  contentStyle: {
    backgroundColor: isDarkMode ? CHART_COLORS.dark.tooltipBg : CHART_COLORS.light.tooltipBg,
    border: `1px solid ${isDarkMode ? CHART_COLORS.dark.tooltipBorder : CHART_COLORS.light.tooltipBorder}`,
    borderRadius: '8px',
    boxShadow: isDarkMode 
      ? `0 4px 6px rgba(0, 0, 0, 0.3), 0 0 20px ${CHART_COLORS.ember.glow}` 
      : '0 4px 6px rgba(0, 0, 0, 0.1)',
    color: isDarkMode ? CHART_COLORS.dark.text : CHART_COLORS.light.text
  },
  labelStyle: { 
    color: isDarkMode ? CHART_COLORS.dark.text : CHART_COLORS.light.text 
  }
});