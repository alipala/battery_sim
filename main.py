from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import logging


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class BatteryConfig(BaseModel):
    capacity: int
    price: float

class PriceAnalyzer:
    def __init__(self):
        self.df = None
        
    def load_data(self, file_content: bytes):
        try:
            from io import BytesIO
            self.df = pd.read_excel(BytesIO(file_content))
            logger.debug(f"Columns in uploaded file: {self.df.columns.tolist()}")
            
            # Parse datetime
            self.df['DateTime'] = pd.to_datetime(self.df['Date Time'], format='mixed', dayfirst=True)
            self.df['Hour'] = self.df['DateTime'].dt.hour
            self.df['Date'] = self.df['DateTime'].dt.date
            self.df['Month'] = self.df['DateTime'].dt.month
            self.df['Year'] = self.df['DateTime'].dt.year
            
            return True
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return False

    def find_daily_trading_opportunities(self, day_data):
        """Find up to 2 profitable trading opportunities in a day"""
        day_data = day_data.sort_values('DateTime')
        opportunities = []
        
        # First trading opportunity
        min_idx = day_data['EUR per kWh'].idxmin()
        min_time = day_data.loc[min_idx, 'DateTime']
        remaining_data = day_data[day_data['DateTime'] > min_time]
        
        if not remaining_data.empty:
            max_idx = remaining_data['EUR per kWh'].idxmax()
            max_time = remaining_data.loc[max_idx, 'DateTime']
            
            profit = day_data.loc[max_idx, 'EUR per kWh'] - day_data.loc[min_idx, 'EUR per kWh']
            if profit > 0:
                opportunities.append({
                    'buy_time': min_time,
                    'buy_price': day_data.loc[min_idx, 'EUR per kWh'],
                    'sell_time': max_time,
                    'sell_price': day_data.loc[max_idx, 'EUR per kWh'],
                    'profit': profit
                })
                
                # Look for second opportunity after first sell
                remaining_data = day_data[day_data['DateTime'] > max_time]
                if not remaining_data.empty:
                    min_idx2 = remaining_data['EUR per kWh'].idxmin()
                    min_time2 = remaining_data.loc[min_idx2, 'DateTime']
                    remaining_data2 = remaining_data[remaining_data['DateTime'] > min_time2]
                    
                    if not remaining_data2.empty:
                        max_idx2 = remaining_data2['EUR per kWh'].idxmax()
                        max_time2 = remaining_data2.loc[max_idx2, 'DateTime']
                        profit2 = remaining_data2.loc[max_idx2, 'EUR per kWh'] - remaining_data.loc[min_idx2, 'EUR per kWh']
                        
                        if profit2 > 0:
                            opportunities.append({
                                'buy_time': min_time2,
                                'buy_price': remaining_data.loc[min_idx2, 'EUR per kWh'],
                                'sell_time': max_time2,
                                'sell_price': remaining_data2.loc[max_idx2, 'EUR per kWh'],
                                'profit': profit2
                            })
        
        return opportunities

    def calculate_daily_profits(self, capacity: int):
        try:
            daily_profits = []
            
            for date in self.df['Date'].unique():
                day_data = self.df[self.df['Date'] == date]
                opportunities = self.find_daily_trading_opportunities(day_data)
                
                total_daily_profit = sum(opp['profit'] * capacity for opp in opportunities)
                
                daily_profits.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'profit': round(total_daily_profit, 2),
                    'transactions': len(opportunities),
                    'opportunities': [
                        {
                            'buy_time': opp['buy_time'].strftime('%H:%M'),
                            'buy_price': round(float(opp['buy_price']), 4),
                            'sell_time': opp['sell_time'].strftime('%H:%M'),
                            'sell_price': round(float(opp['sell_price']), 4),
                            'profit': round(float(opp['profit'] * capacity), 2)
                        }
                        for opp in opportunities
                    ]
                })
            
            return daily_profits
        except Exception as e:
            logger.error(f"Error calculating daily profits: {str(e)}")
            raise

    def calculate_monthly_profits(self, capacity: int):
        try:
            daily_data = pd.DataFrame([(d['date'], d['profit']) for d in self.calculate_daily_profits(capacity)],
                                    columns=['date', 'profit'])
            daily_data['date'] = pd.to_datetime(daily_data['date'])
            daily_data['month'] = daily_data['date'].dt.strftime('%Y-%m')
            
            monthly_stats = daily_data.groupby('month').agg({
                'profit': ['sum', 'mean', 'max', 'min', 'count']
            }).reset_index()
            
            monthly_stats.columns = ['month', 'total_profit', 'avg_profit', 'max_profit', 'min_profit', 'trading_days']
            
            return monthly_stats.to_dict('records')
        except Exception as e:
            logger.error(f"Error calculating monthly profits: {str(e)}")
            raise

    def calculate_yearly_summary(self, capacity: int, battery_price: float):
        try:
            monthly_data = pd.DataFrame(self.calculate_monthly_profits(capacity))
            yearly_profit = monthly_data['total_profit'].sum()
            
            # Calculate ROI
            roi_years = battery_price / yearly_profit if yearly_profit > 0 else float('inf')
            annual_return_percentage = (yearly_profit / battery_price) * 100
            
            # Calculate break-even date
            days_to_breakeven = (battery_price / (yearly_profit / 365))
            breakeven_date = pd.Timestamp.now() + pd.Timedelta(days=days_to_breakeven)
            
            return {
                'total_profit': round(yearly_profit, 2),
                'roi_years': round(roi_years, 2),
                'annual_return_percentage': round(annual_return_percentage, 2),
                'monthly_average': round(yearly_profit / 12, 2),
                'breakeven_date': breakeven_date.strftime('%Y-%m-%d'),
                'total_investment': battery_price
            }
        except Exception as e:
            logger.error(f"Error calculating yearly summary: {str(e)}")
            raise

# Initialize analyzer
price_analyzer = PriceAnalyzer()

# Health check endpoint
@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Serve frontend
@app.get("/")
async def read_root():
    try:
        return FileResponse('static/index.html')
    except Exception as e:
        logger.error(f"Error serving index.html: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error"}
        )

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        if price_analyzer.load_data(contents):
            return {"status": "success", "message": "File uploaded and processed successfully"}
        else:
            raise HTTPException(status_code=400, detail="Error processing file")
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/analyze")
async def analyze_data(config: BatteryConfig):
    try:
        if price_analyzer.df is None:
            raise HTTPException(status_code=400, detail="No data loaded. Please upload a file first.")
        
        return {
            "daily": price_analyzer.calculate_daily_profits(config.capacity),
            "monthly": price_analyzer.calculate_monthly_profits(config.capacity),
            "yearly": price_analyzer.calculate_yearly_summary(config.capacity, config.price)
        }
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    # Ensure static directory exists
    os.makedirs("static/js", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Start server
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False,  # Disable reload in production
        workers=4  # Multiple workers for better performance
    )