"""
Implementation Guide for Indonesian Quantitative Trading System
Step-by-step deployment and configuration instructions
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
import yfinance as yf

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from feature_engineering import IDXFeatureEngineer
from model_ensemble import IDXQuantitativeModel
from signal_generator import SignalGenerator
from main_pipeline import TradingPipeline


class IDXTradingSystemSetup:
    """
    Complete setup and deployment guide for the Indonesian quantitative trading system
    """

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models"
        self.signals_dir = self.base_dir / "signals"
        self.reports_dir = self.base_dir / "reports"

        # Create directory structure
        self._create_directories()

    def _create_directories(self):
        """Create necessary directory structure"""
        directories = [self.data_dir, self.models_dir, self.signals_dir, self.reports_dir]
        for directory in directories:
            directory.mkdir(exist_ok=True)
        print("✓ Directory structure created")

    def step1_data_collection_setup(self):
        """
        Step 1: Set up data collection infrastructure
        """
        print("\n=== STEP 1: DATA COLLECTION SETUP ===")

        # LQ45 stocks list (top 45 liquid Indonesian stocks)
        lq45_stocks = [
            'BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'BBNI.JK',  # Banking
            'TLKM.JK', 'EXCL.JK',  # Telecommunications
            'ASII.JK', 'AALI.JK', 'UNTR.JK',  # Automotive & Plantation
            'UNVR.JK', 'INDF.JK', 'ICBP.JK', 'KLBF.JK',  # Consumer Goods
            'HMSP.JK', 'GGRM.JK',  # Tobacco
            'ADRO.JK', 'PTBA.JK', 'ITMG.JK',  # Mining
            'PGAS.JK', 'AKRA.JK',  # Energy & Trading
            'WSKT.JK', 'WIKA.JK', 'PTPP.JK',  # Construction
            'SMGR.JK', 'INTP.JK',  # Cement
            'JSMR.JK', 'BMTR.JK',  # Infrastructure
            'LPKR.JK', 'BSDE.JK',  # Property
            'ERAA.JK', 'ESSA.JK',  # Healthcare
            'AMRT.JK', 'MAPI.JK',  # Retail
            'SCMA.JK', 'SILO.JK',  # Others
        ]

        # Save stock list
        stock_list_file = self.data_dir / "lq45_stocks.txt"
        with open(stock_list_file, 'w') as f:
            for stock in lq45_stocks:
                f.write(f"{stock}\n")

        print(f"✓ LQ45 stock list saved to {stock_list_file}")

        # Download sample historical data
        print("Downloading sample historical data...")
        self._download_sample_data(lq45_stocks[:10])  # First 10 stocks for testing

        return lq45_stocks

    def _download_sample_data(self, stock_list: list):
        """Download sample data for initial testing"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)  # 2 years of data

        all_data = []
        for stock in stock_list:
            try:
                print(f"  Downloading {stock}...")
                data = yf.download(stock, start=start_date, end=end_date, progress=False)
                if not data.empty:
                    data['stock_code'] = stock
                    data = data.reset_index()
                    all_data.append(data)
            except Exception as e:
                print(f"  Failed to download {stock}: {e}")

        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            combined_data.columns = [col.lower() for col in combined_data.columns]

            # Add sector information (simplified mapping)
            sector_mapping = {
                'BBCA.JK': 'BANKING', 'BBRI.JK': 'BANKING', 'BMRI.JK': 'BANKING', 'BBNI.JK': 'BANKING',
                'TLKM.JK': 'TELECOM', 'EXCL.JK': 'TELECOM',
                'ASII.JK': 'AUTOMOTIVE', 'AALI.JK': 'PLANTATION', 'UNTR.JK': 'HEAVY_EQUIPMENT',
                'UNVR.JK': 'CONSUMER', 'INDF.JK': 'CONSUMER', 'ICBP.JK': 'CONSUMER', 'KLBF.JK': 'PHARMA'
            }

            combined_data['sector'] = combined_data['stock_code'].map(sector_mapping).fillna('OTHER')

            # Save to file
            data_file = self.data_dir / "sample_market_data.csv"
            combined_data.to_csv(data_file, index=False)
            print(f"✓ Sample data saved to {data_file}")

    def step2_feature_engineering_demo(self):
        """
        Step 2: Demonstrate feature engineering capabilities
        """
        print("\n=== STEP 2: FEATURE ENGINEERING DEMO ===")

        # Load sample data
        data_file = self.data_dir / "sample_market_data.csv"
        if not data_file.exists():
            print("❌ Sample data not found. Run step 1 first.")
            return

        market_data = pd.read_csv(data_file)
        print(f"✓ Loaded {len(market_data)} records")

        # Initialize feature engineer
        feature_engineer = IDXFeatureEngineer()

        # Generate features for one stock as example
        bbca_data = market_data[market_data['stock_code'] == 'BBCA.JK'].copy()
        if bbca_data.empty:
            print("❌ BBCA data not found")
            return

        print("Generating technical features for BBCA...")
        technical_features = feature_engineer.generate_technical_features(bbca_data)

        print(f"✓ Generated {len(technical_features.columns)} features")
        print("Sample features:")
        feature_sample = technical_features[['stock_code', 'date', 'close', 'rsi_14', 'macd', 'bb_position', 'volume_ratio']].tail()
        print(feature_sample.to_string())

        # Save engineered features
        features_file = self.data_dir / "sample_features.csv"
        technical_features.to_csv(features_file, index=False)
        print(f"✓ Features saved to {features_file}")

        return technical_features

    def step3_model_training_demo(self):
        """
        Step 3: Train ensemble models with sample data
        """
        print("\n=== STEP 3: MODEL TRAINING DEMO ===")

        # Load features
        features_file = self.data_dir / "sample_features.csv"
        if not features_file.exists():
            print("❌ Features file not found. Run step 2 first.")
            return

        features_data = pd.read_csv(features_file)
        print(f"✓ Loaded features: {features_data.shape}")

        # Initialize and train ensemble model
        print("Training ensemble model...")
        model = IDXQuantitativeModel()

        try:
            training_metrics = model.train(features_data)
            print("✓ Model training completed!")

            print("\nTraining Metrics:")
            for model_name, metrics in training_metrics.items():
                print(f"  {model_name.upper()}:")
                for metric, value in metrics.items():
                    if isinstance(value, (int, float)):
                        print(f"    {metric}: {value:.4f}")

            # Save trained model
            model_file = self.models_dir / "idx_quant_model.pkl"
            model.save_models(str(model_file))
            print(f"✓ Model saved to {model_file}")

            # Test prediction
            print("\nTesting prediction...")
            predictions = model.predict(features_data.tail(50))
            print("✓ Prediction test successful")
            print(f"Sample ensemble scores: {predictions['ensemble_score'][:5]}")

            return model

        except Exception as e:
            print(f"❌ Model training failed: {e}")
            return None

    def step4_signal_generation_demo(self):
        """
        Step 4: Generate trading signals
        """
        print("\n=== STEP 4: SIGNAL GENERATION DEMO ===")

        # Load model
        model_file = self.models_dir / "idx_quant_model.pkl"
        if not model_file.exists():
            print("❌ Model file not found. Run step 3 first.")
            return

        try:
            model = IDXQuantitativeModel.load_models(str(model_file))
            print("✓ Model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return

        # Load latest data
        features_file = self.data_dir / "sample_features.csv"
        features_data = pd.read_csv(features_file)

        # Use recent data for signal generation
        recent_data = features_data.groupby('stock_code').tail(1).reset_index(drop=True)
        print(f"✓ Using recent data for {len(recent_data)} stocks")

        # Generate predictions
        predictions = model.predict(recent_data)
        print("✓ Predictions generated")

        # Initialize signal generator
        signal_generator = SignalGenerator()

        # Generate signals
        signals = signal_generator.generate_daily_signals(predictions, recent_data)
        print(f"✓ Generated {len(signals)} trading signals")

        # Display signal summary
        signal_summary = signals['signal_type'].value_counts()
        print("\nSignal Summary:")
        for signal_type, count in signal_summary.items():
            print(f"  {signal_type}: {count}")

        # Show top signals
        print("\nTop 5 Signals by Confidence:")
        top_signals = signals.nlargest(5, 'confidence')[
            ['stock_code', 'signal_type', 'confidence', 'position_size', 'current_price']
        ]
        print(top_signals.to_string(index=False))

        # Generate portfolio summary
        portfolio_summary = signal_generator.generate_portfolio_summary(signals)
        print(f"\nPortfolio Summary:")
        print(f"  Active Signals: {portfolio_summary['active_signals']}")
        print(f"  Total Exposure: {portfolio_summary['total_long_exposure']:.1%}")
        print(f"  Cash Available: {portfolio_summary['cash_available']:.1%}")

        # Save signals
        signals_file = self.signals_dir / f"demo_signals_{datetime.now().strftime('%Y%m%d')}.csv"
        signals.to_csv(signals_file, index=False)
        print(f"✓ Signals saved to {signals_file}")

        return signals, portfolio_summary

    def step5_pipeline_integration_demo(self):
        """
        Step 5: Demonstrate complete pipeline integration
        """
        print("\n=== STEP 5: PIPELINE INTEGRATION DEMO ===")

        # Initialize pipeline
        pipeline = TradingPipeline()
        print("✓ Pipeline initialized")

        # Load model
        if pipeline.load_model():
            print("✓ Model loaded into pipeline")
        else:
            print("❌ Failed to load model into pipeline")
            return

        # Run manual pipeline execution
        print("Running complete pipeline...")
        try:
            result = pipeline.run_manual_pipeline()
            print("✓ Pipeline execution completed")

            print("\nPipeline Results:")
            for key, value in result.items():
                if key != 'portfolio_summary':
                    print(f"  {key}: {value}")

            return result

        except Exception as e:
            print(f"❌ Pipeline execution failed: {e}")
            return None

    def step6_deployment_checklist(self):
        """
        Step 6: Production deployment checklist
        """
        print("\n=== STEP 6: DEPLOYMENT CHECKLIST ===")

        checklist = [
            ("Data Sources", "Configure real-time IDX data feeds"),
            ("Database", "Set up PostgreSQL for data storage"),
            ("Scheduling", "Configure daily execution at 8:30 AM WIB"),
            ("Monitoring", "Set up system monitoring and alerts"),
            ("Backup", "Configure model and data backup"),
            ("Security", "Implement API security and access controls"),
            ("Testing", "Complete end-to-end testing"),
            ("Documentation", "Finalize operational procedures"),
            ("Compliance", "Ensure regulatory compliance (OJK)"),
            ("Team Training", "Train operators on system usage")
        ]

        print("Production Deployment Checklist:")
        for i, (category, task) in enumerate(checklist, 1):
            print(f"  {i:2d}. {category:15s}: {task}")

        # Create deployment configuration template
        config_template = {
            "data_collection": {
                "primary_source": "idx_official_api",
                "backup_sources": ["yahoo_finance", "google_finance"],
                "update_frequency": "real_time",
                "historical_data_years": 3
            },
            "model_config": {
                "retrain_frequency": "weekly",
                "performance_threshold": 0.6,
                "auto_fallback": True
            },
            "risk_management": {
                "max_position_size": 0.05,
                "max_sector_concentration": 0.25,
                "daily_var_limit": 0.03,
                "drawdown_limit": 0.10
            },
            "alerts": {
                "email_recipients": ["trader@company.com"],
                "telegram_chat_id": "your_chat_id",
                "alert_thresholds": {
                    "high_confidence": 0.8,
                    "large_position": 0.03
                }
            }
        }

        config_file = self.base_dir / "production_config.json"
        import json
        with open(config_file, 'w') as f:
            json.dump(config_template, f, indent=2)

        print(f"\n✓ Deployment config template saved to {config_file}")

    def run_complete_demo(self):
        """
        Run complete system demonstration
        """
        print("🚀 INDONESIAN QUANTITATIVE TRADING SYSTEM DEMO")
        print("=" * 60)

        try:
            # Step 1: Data Collection
            lq45_stocks = self.step1_data_collection_setup()

            # Step 2: Feature Engineering
            features = self.step2_feature_engineering_demo()
            if features is None:
                return

            # Step 3: Model Training
            model = self.step3_model_training_demo()
            if model is None:
                return

            # Step 4: Signal Generation
            signals, portfolio = self.step4_signal_generation_demo()
            if signals is None:
                return

            # Step 5: Pipeline Integration
            pipeline_result = self.step5_pipeline_integration_demo()

            # Step 6: Deployment Checklist
            self.step6_deployment_checklist()

            print("\n🎉 DEMO COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("The system is now ready for production deployment.")
            print("Follow the deployment checklist for go-live preparation.")

        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()

    def get_system_status(self):
        """
        Check current system status and files
        """
        print("\n=== SYSTEM STATUS ===")

        files_to_check = [
            ("Sample Data", self.data_dir / "sample_market_data.csv"),
            ("Features", self.data_dir / "sample_features.csv"),
            ("Trained Model", self.models_dir / "idx_quant_model.pkl"),
            ("Latest Signals", self.signals_dir / f"demo_signals_{datetime.now().strftime('%Y%m%d')}.csv"),
            ("Config Template", self.base_dir / "production_config.json")
        ]

        status = {}
        for name, filepath in files_to_check:
            exists = filepath.exists()
            size = filepath.stat().st_size if exists else 0
            status[name] = {
                'exists': exists,
                'path': str(filepath),
                'size_mb': size / (1024 * 1024) if exists else 0
            }
            status_icon = "✓" if exists else "❌"
            print(f"  {status_icon} {name:15s}: {filepath}")

        return status


def main():
    """
    Main function to run the implementation demo
    """
    import argparse

    parser = argparse.ArgumentParser(description='IDX Trading System Implementation Guide')
    parser.add_argument('--step', type=int, choices=range(1, 7),
                      help='Run specific step (1-6)')
    parser.add_argument('--full-demo', action='store_true',
                      help='Run complete demonstration')
    parser.add_argument('--status', action='store_true',
                      help='Check system status')

    args = parser.parse_args()

    setup = IDXTradingSystemSetup()

    if args.status:
        setup.get_system_status()
    elif args.full_demo:
        setup.run_complete_demo()
    elif args.step:
        step_methods = {
            1: setup.step1_data_collection_setup,
            2: setup.step2_feature_engineering_demo,
            3: setup.step3_model_training_demo,
            4: setup.step4_signal_generation_demo,
            5: setup.step5_pipeline_integration_demo,
            6: setup.step6_deployment_checklist
        }
        step_methods[args.step]()
    else:
        print("Indonesian Quantitative Trading System Implementation Guide")
        print("Usage examples:")
        print("  python implementation_guide.py --full-demo")
        print("  python implementation_guide.py --step 1")
        print("  python implementation_guide.py --status")


if __name__ == "__main__":
    main()