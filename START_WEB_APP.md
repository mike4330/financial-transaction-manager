# 🚀 React + Flask Transaction Manager

## Quick Start Guide

### 1. Start the Flask API Backend
```bash
# In terminal 1 (from /var/www/html/bank/)
python3 api_server.py
```
This starts the API server on **http://localhost:5000**

### 2. Start the React Frontend
```bash
# In terminal 2 (from /var/www/html/bank/)
cd frontend
npm run dev
```
This starts the React app on **http://localhost:3001** (or next available port)

### 3. Access the Application
Open your browser to: **http://localhost:3001**

---

## 🌟 Features Available

### Dashboard (/)
- **Real-time Statistics**: Live transaction counts, account summaries, categorization status
- **Backend Status Indicator**: Green "Backend OK" pill showing Flask API connection
- **Clean Card Layout**: Professional dashboard cards with key financial metrics
- **Responsive Design**: Works seamlessly on desktop and mobile

### Interactive Visualizations
- **Grocery Spending Chart**: Time-series visualization showing grocery spending trends
- **Global Time Range Controls**: 1 Month, 3 Months, 6 Months, 1 Year, 2 Years, All Time
- **Dynamic Updates**: Charts automatically update when time range selection changes
- **Professional Styling**: Built with Recharts for publication-quality charts

### Transaction Manager (Planned)
- Professional AG-Grid spreadsheet interface
- Advanced filtering (account, category, date, type)
- Bulk categorization with multi-select
- Pagination and sorting
- Real-time updates

### API Endpoints (http://localhost:5000/api/)
- `GET /health` - Health check
- `GET /transactions` - List with filtering
- `GET /categories` - Categories and subcategories
- `GET /stats` - Dashboard statistics
- `POST /transactions/bulk-categorize` - Bulk operations

---

## 🛠 Tech Stack

### Backend
- **Flask** - Python web framework
- **SQLite** - Your existing database (unchanged)
- **CORS** - Cross-origin requests enabled

### Frontend  
- **React 18** - Modern UI framework
- **TypeScript** - Type safety and better development experience
- **Recharts** - Professional charting library for data visualization
- **Custom CSS** - Responsive styling with utility classes
- **React Context API** - Global state management (time ranges)
- **Vite** - Fast build tool with hot reload

---

## 📁 File Structure
```
/var/www/html/bank/
├── main.py                 # Your existing CLI (unchanged)
├── api_server.py          # Flask REST API server  
├── payee_extractor.py     # Payee extraction utility
├── frontend/              # React TypeScript application
│   ├── src/components/    # React components (GroceryChart, TimeRangeSelector)
│   ├── src/contexts/      # React contexts (TimeRangeContext)
│   ├── App.simple.tsx     # Main application component
│   └── main.tsx           # React entry point
└── (existing files untouched)
```

---

## 🔧 Development Notes

- **Your existing Python CLI tools remain fully functional**
- Flask API runs separately from main.py
- React dev server auto-reloads on changes
- API calls are proxied through Vite dev server
- All your existing CSV processing, AI classification, etc. still works

---

## 🎯 Next Steps

1. **Extract payees**: Run `python3 payee_extractor.py --apply` to improve transaction data
2. **Add more visualizations**: Extend the dashboard with additional charts
3. **Implement transaction manager**: Add AG-Grid spreadsheet interface for transaction editing
4. **Add authentication** if needed for production deployment
5. **Deploy to production** when ready

---

**Happy coding! 🎉**