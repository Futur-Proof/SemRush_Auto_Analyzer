#!/usr/bin/env python3
"""
Growth Projector for New Business Launch
Generates 3-month and 6-month traffic, orders, and revenue projections
based on paid media benchmarks and organic growth models.
"""

import os
import sys
import json
import csv
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.config_loader import (
        load_config, get_output_dir, get_data_dir, ensure_directories,
        get_target_name
    )
except ImportError:
    from config_loader import (
        load_config, get_output_dir, get_data_dir, ensure_directories,
        get_target_name
    )


class GrowthProjector:
    """
    Projects traffic, orders, and revenue growth for new business launches.
    Uses paid media benchmarks and organic growth models.
    """

    # Default industry benchmarks (used if no benchmark data available)
    DEFAULT_BENCHMARKS = {
        'luxury_ecommerce': {
            'avg_cpc': 2.50,
            'avg_cpm': 18.00,
            'avg_ctr': 1.2,  # percent
            'conversion_rate_month_1_3': 1.5,  # percent, new brand no social proof
            'conversion_rate_month_4_6': 2.5,  # percent, with reviews/retargeting
            'conversion_rate_month_7_12': 3.5,  # percent, established
            'organic_growth_curve': {  # percent of total traffic from organic
                1: 5, 2: 7, 3: 10, 4: 12, 5: 15, 6: 18,
                7: 22, 8: 25, 9: 28, 10: 30, 11: 32, 12: 35
            },
            'cpc_optimization_curve': {  # CPC reduction multiplier by month
                1: 1.0, 2: 0.95, 3: 0.90, 4: 0.85, 5: 0.82, 6: 0.80,
                7: 0.78, 8: 0.76, 9: 0.75, 10: 0.74, 11: 0.73, 12: 0.72
            }
        }
    }

    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = load_config(config_path)
        ensure_directories(self.config)

        self.output_dir = get_output_dir(self.config)
        self.data_dir = get_data_dir(self.config)
        self.projections_dir = os.path.join(self.output_dir, 'projections')
        os.makedirs(self.projections_dir, exist_ok=True)

        self.target_name = get_target_name(self.config)
        self.benchmarks = self._load_benchmarks()
        self.projection_config = self.config.get('projections', {})

    def _load_benchmarks(self) -> Dict:
        """Load benchmark data from paid_media_benchmarks.json if available."""
        benchmark_path = os.path.join(self.data_dir, 'paid_media', 'paid_media_benchmarks.json')

        if os.path.exists(benchmark_path):
            print(f"[OK] Loading benchmarks from {benchmark_path}")
            with open(benchmark_path, 'r') as f:
                return json.load(f)
        else:
            print("[Warning] No benchmark data found, using industry defaults")
            return {'industry_averages': self.DEFAULT_BENCHMARKS['luxury_ecommerce']}

    def calculate_monthly_projection(
        self,
        month: int,
        monthly_ad_spend: float,
        aov: float,
        base_cpc: float,
        base_conversion_rate: float,
        industry: str = 'luxury_ecommerce'
    ) -> Dict:
        """
        Calculate projections for a single month.

        Args:
            month: Month number (1-12)
            monthly_ad_spend: Total ad spend for the month
            aov: Average Order Value
            base_cpc: Starting Cost Per Click
            base_conversion_rate: Starting conversion rate (percent)
            industry: Industry type for benchmark curves

        Returns:
            Dict with all projection metrics for the month
        """
        defaults = self.DEFAULT_BENCHMARKS.get(industry, self.DEFAULT_BENCHMARKS['luxury_ecommerce'])

        # Apply optimization curves
        cpc_multiplier = defaults['cpc_optimization_curve'].get(month, 0.75)
        effective_cpc = base_cpc * cpc_multiplier

        # Conversion rate improves over time
        if month <= 3:
            effective_cr = base_conversion_rate
        elif month <= 6:
            effective_cr = base_conversion_rate * 1.5  # 50% improvement by month 6
        else:
            effective_cr = base_conversion_rate * 2.0  # 100% improvement by month 12

        # Calculate paid traffic
        paid_clicks = monthly_ad_spend / effective_cpc
        paid_orders = paid_clicks * (effective_cr / 100)
        paid_revenue = paid_orders * aov

        # Calculate organic traffic (grows over time for new brands)
        organic_pct = defaults['organic_growth_curve'].get(month, 35) / 100
        # Organic traffic is organic_pct of total, so paid is (1 - organic_pct)
        # Total clicks = paid_clicks / (1 - organic_pct)
        total_traffic = paid_clicks / (1 - organic_pct) if organic_pct < 1 else paid_clicks
        organic_traffic = total_traffic * organic_pct

        # Organic has higher conversion (warmer traffic)
        organic_cr = effective_cr * 1.3  # 30% higher than paid
        organic_orders = organic_traffic * (organic_cr / 100)
        organic_revenue = organic_orders * aov

        # Total metrics
        total_orders = paid_orders + organic_orders
        total_revenue = paid_revenue + organic_revenue

        # ROAS calculation
        roas = total_revenue / monthly_ad_spend if monthly_ad_spend > 0 else 0

        return {
            'month': month,
            'ad_spend': round(monthly_ad_spend, 2),
            'effective_cpc': round(effective_cpc, 2),
            'effective_cr': round(effective_cr, 2),
            'paid_traffic': round(paid_clicks),
            'paid_orders': round(paid_orders, 1),
            'paid_revenue': round(paid_revenue, 2),
            'organic_pct': round(organic_pct * 100, 1),
            'organic_traffic': round(organic_traffic),
            'organic_orders': round(organic_orders, 1),
            'organic_revenue': round(organic_revenue, 2),
            'total_traffic': round(total_traffic),
            'total_orders': round(total_orders, 1),
            'total_revenue': round(total_revenue, 2),
            'roas': round(roas, 2),
            'cac': round(monthly_ad_spend / total_orders, 2) if total_orders > 0 else 0
        }

    def generate_projections(
        self,
        monthly_ad_spend: float,
        aov: float,
        cpc: Optional[float] = None,
        conversion_rate: Optional[float] = None,
        months: int = 6
    ) -> Dict:
        """
        Generate full projection model for specified number of months.

        Args:
            monthly_ad_spend: Monthly advertising budget
            aov: Average Order Value
            cpc: Cost Per Click (uses benchmark if not provided)
            conversion_rate: Starting conversion rate (uses benchmark if not provided)
            months: Number of months to project (default 6)

        Returns:
            Dict with monthly projections and summary
        """
        # Use benchmark data or defaults
        if cpc is None:
            cpc = self.benchmarks.get('industry_averages', {}).get('avg_cpc')
            if cpc is None:
                cpc = self.DEFAULT_BENCHMARKS['luxury_ecommerce']['avg_cpc']

        if conversion_rate is None:
            conversion_rate = self.DEFAULT_BENCHMARKS['luxury_ecommerce']['conversion_rate_month_1_3']

        print(f"\n{'='*60}")
        print(f"GROWTH PROJECTIONS FOR {self.target_name.upper()}")
        print(f"{'='*60}")
        print(f"\nInputs:")
        print(f"  Monthly Ad Spend: ${monthly_ad_spend:,.2f}")
        print(f"  Average Order Value: ${aov:,.2f}")
        print(f"  Base CPC: ${cpc:.2f}")
        print(f"  Base Conversion Rate: {conversion_rate}%")
        print(f"  Projection Period: {months} months")

        projections = {
            'inputs': {
                'monthly_ad_spend': monthly_ad_spend,
                'aov': aov,
                'base_cpc': cpc,
                'base_conversion_rate': conversion_rate,
                'months': months
            },
            'monthly': [],
            'summary': {},
            'generated_at': datetime.now().isoformat()
        }

        # Generate monthly projections
        for month in range(1, months + 1):
            monthly = self.calculate_monthly_projection(
                month=month,
                monthly_ad_spend=monthly_ad_spend,
                aov=aov,
                base_cpc=cpc,
                base_conversion_rate=conversion_rate
            )
            projections['monthly'].append(monthly)

        # Calculate summary
        total_spend = sum(m['ad_spend'] for m in projections['monthly'])
        total_revenue = sum(m['total_revenue'] for m in projections['monthly'])
        total_orders = sum(m['total_orders'] for m in projections['monthly'])

        # 3-month summary
        m3_spend = sum(m['ad_spend'] for m in projections['monthly'][:3])
        m3_revenue = sum(m['total_revenue'] for m in projections['monthly'][:3])
        m3_orders = sum(m['total_orders'] for m in projections['monthly'][:3])
        m3_organic_pct = projections['monthly'][2]['organic_pct'] if len(projections['monthly']) >= 3 else 0

        # 6-month summary
        m6_organic_pct = projections['monthly'][5]['organic_pct'] if len(projections['monthly']) >= 6 else projections['monthly'][-1]['organic_pct']

        projections['summary'] = {
            '3_month': {
                'total_spend': round(m3_spend, 2),
                'total_revenue': round(m3_revenue, 2),
                'total_orders': round(m3_orders, 1),
                'roas': round(m3_revenue / m3_spend, 2) if m3_spend > 0 else 0,
                'organic_traffic_pct': m3_organic_pct,
                'paid_traffic_pct': round(100 - m3_organic_pct, 1)
            },
            '6_month': {
                'total_spend': round(total_spend, 2),
                'total_revenue': round(total_revenue, 2),
                'total_orders': round(total_orders, 1),
                'roas': round(total_revenue / total_spend, 2) if total_spend > 0 else 0,
                'organic_traffic_pct': m6_organic_pct,
                'paid_traffic_pct': round(100 - m6_organic_pct, 1)
            },
            'avg_cac': round(total_spend / total_orders, 2) if total_orders > 0 else 0
        }

        return projections

    def print_projection_table(self, projections: Dict):
        """Print formatted projection table."""
        print(f"\n{'='*100}")
        print("MONTHLY PROJECTIONS")
        print(f"{'='*100}")
        print(f"{'Month':>6} {'Ad Spend':>12} {'CPC':>8} {'Paid Traffic':>14} {'Organic %':>10} {'Orders':>10} {'Revenue':>14} {'ROAS':>8} {'CAC':>10}")
        print("-" * 100)

        for m in projections['monthly']:
            print(f"{m['month']:>6} ${m['ad_spend']:>10,.0f} ${m['effective_cpc']:>6.2f} {m['paid_traffic']:>13,} {m['organic_pct']:>9.1f}% {m['total_orders']:>9.0f} ${m['total_revenue']:>12,.0f} {m['roas']:>7.2f}x ${m['cac']:>8.0f}")

        print("-" * 100)

        # Print summaries
        s3 = projections['summary']['3_month']
        s6 = projections['summary']['6_month']

        print(f"\n3-MONTH SUMMARY:")
        print(f"  Total Spend: ${s3['total_spend']:,.2f}")
        print(f"  Total Revenue: ${s3['total_revenue']:,.2f}")
        print(f"  Total Orders: {s3['total_orders']:,.0f}")
        print(f"  ROAS: {s3['roas']}x")
        print(f"  Traffic Split: {s3['paid_traffic_pct']}% Paid / {s3['organic_traffic_pct']}% Organic")

        print(f"\n6-MONTH SUMMARY:")
        print(f"  Total Spend: ${s6['total_spend']:,.2f}")
        print(f"  Total Revenue: ${s6['total_revenue']:,.2f}")
        print(f"  Total Orders: {s6['total_orders']:,.0f}")
        print(f"  ROAS: {s6['roas']}x")
        print(f"  Traffic Split: {s6['paid_traffic_pct']}% Paid / {s6['organic_traffic_pct']}% Organic")
        print(f"  Average CAC: ${projections['summary']['avg_cac']:,.2f}")

    def save_projections(self, projections: Dict, filename_prefix: str = 'growth_projection'):
        """Save projections to JSON and CSV files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save JSON
        json_path = os.path.join(self.projections_dir, f"{filename_prefix}_{timestamp}.json")
        with open(json_path, 'w') as f:
            json.dump(projections, f, indent=2)
        print(f"\n[Saved] {json_path}")

        # Save CSV
        csv_path = os.path.join(self.projections_dir, f"{filename_prefix}_{timestamp}.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Month', 'Ad Spend', 'Effective CPC', 'Conversion Rate',
                'Paid Traffic', 'Paid Orders', 'Paid Revenue',
                'Organic %', 'Organic Traffic', 'Organic Orders', 'Organic Revenue',
                'Total Traffic', 'Total Orders', 'Total Revenue', 'ROAS', 'CAC'
            ])
            for m in projections['monthly']:
                writer.writerow([
                    m['month'], m['ad_spend'], m['effective_cpc'], m['effective_cr'],
                    m['paid_traffic'], m['paid_orders'], m['paid_revenue'],
                    m['organic_pct'], m['organic_traffic'], m['organic_orders'], m['organic_revenue'],
                    m['total_traffic'], m['total_orders'], m['total_revenue'], m['roas'], m['cac']
                ])
        print(f"[Saved] {csv_path}")

        # Save summary report
        report_path = os.path.join(self.projections_dir, f"{filename_prefix}_report_{timestamp}.txt")
        with open(report_path, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write(f"GROWTH PROJECTION REPORT: {self.target_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")

            f.write("PROJECTION INPUTS:\n")
            f.write("-" * 40 + "\n")
            inputs = projections['inputs']
            f.write(f"Monthly Ad Spend: ${inputs['monthly_ad_spend']:,.2f}\n")
            f.write(f"Average Order Value (AOV): ${inputs['aov']:,.2f}\n")
            f.write(f"Base Cost Per Click (CPC): ${inputs['base_cpc']:.2f}\n")
            f.write(f"Base Conversion Rate: {inputs['base_conversion_rate']}%\n")
            f.write(f"Projection Period: {inputs['months']} months\n")

            f.write("\n\n3-MONTH PROJECTION:\n")
            f.write("-" * 40 + "\n")
            s3 = projections['summary']['3_month']
            f.write(f"Total Marketing Spend: ${s3['total_spend']:,.2f}\n")
            f.write(f"Projected Revenue: ${s3['total_revenue']:,.2f}\n")
            f.write(f"Projected Orders: {s3['total_orders']:,.0f}\n")
            f.write(f"Return on Ad Spend (ROAS): {s3['roas']}x\n")
            f.write(f"Traffic Split: {s3['paid_traffic_pct']}% Paid / {s3['organic_traffic_pct']}% Organic\n")

            f.write("\n\n6-MONTH PROJECTION:\n")
            f.write("-" * 40 + "\n")
            s6 = projections['summary']['6_month']
            f.write(f"Total Marketing Spend: ${s6['total_spend']:,.2f}\n")
            f.write(f"Projected Revenue: ${s6['total_revenue']:,.2f}\n")
            f.write(f"Projected Orders: {s6['total_orders']:,.0f}\n")
            f.write(f"Return on Ad Spend (ROAS): {s6['roas']}x\n")
            f.write(f"Traffic Split: {s6['paid_traffic_pct']}% Paid / {s6['organic_traffic_pct']}% Organic\n")
            f.write(f"Average Customer Acquisition Cost: ${projections['summary']['avg_cac']:,.2f}\n")

            f.write("\n\nKEY ASSUMPTIONS:\n")
            f.write("-" * 40 + "\n")
            f.write("1. CPC optimizes 5-10% per month as algorithms learn\n")
            f.write("2. Conversion rate improves 50% by month 6 (reviews, retargeting)\n")
            f.write("3. Organic traffic grows from ~5% to ~18% over 6 months\n")
            f.write("4. Organic traffic converts 30% higher than paid (warmer)\n")
            f.write("5. New domain SEO takes 2-3 months to show results\n")

            f.write("\n\nVALIDATION NOTES:\n")
            f.write("-" * 40 + "\n")
            f.write("- These projections are based on industry benchmarks\n")
            f.write("- Actual results will vary based on creative quality,\n")
            f.write("  targeting precision, and market conditions\n")
            f.write("- Review and adjust monthly based on actual performance\n")
            f.write("- The 90% paid / 10% organic split in month 1 is typical\n")
            f.write("- The ~80% paid / 20% organic split by month 6 requires\n")
            f.write("  consistent SEO and content investment\n")

        print(f"[Saved] {report_path}")

        return json_path, csv_path, report_path

    def run_interactive(self):
        """Run interactive projection session."""
        print("\n" + "=" * 60)
        print("GROWTH PROJECTOR - Interactive Mode")
        print("=" * 60)

        # Get inputs
        try:
            monthly_spend = float(input("\nMonthly Ad Spend ($): ").replace(',', '').replace('$', ''))
            aov = float(input("Average Order Value ($): ").replace(',', '').replace('$', ''))

            cpc_input = input("Cost Per Click ($ or Enter for benchmark): ").strip()
            cpc = float(cpc_input.replace('$', '')) if cpc_input else None

            cr_input = input("Conversion Rate (% or Enter for benchmark): ").strip()
            cr = float(cr_input.replace('%', '')) if cr_input else None

            months_input = input("Projection months (default 6): ").strip()
            months = int(months_input) if months_input else 6

        except ValueError as e:
            print(f"[Error] Invalid input: {e}")
            return

        # Generate projections
        projections = self.generate_projections(
            monthly_ad_spend=monthly_spend,
            aov=aov,
            cpc=cpc,
            conversion_rate=cr,
            months=months
        )

        # Print and save
        self.print_projection_table(projections)
        self.save_projections(projections)

    def run_from_config(self):
        """Run projection from config file settings."""
        proj_config = self.config.get('projections', {})

        if not proj_config:
            print("[Error] No 'projections' section in config file")
            print("Add projections config or use --interactive mode")
            return None

        monthly_spend = proj_config.get('monthly_ad_spend', 5000)
        aov = proj_config.get('aov', 100)
        cpc = proj_config.get('cpc')
        cr = proj_config.get('conversion_rate')
        months = proj_config.get('months', 6)

        projections = self.generate_projections(
            monthly_ad_spend=monthly_spend,
            aov=aov,
            cpc=cpc,
            conversion_rate=cr,
            months=months
        )

        self.print_projection_table(projections)
        self.save_projections(projections)

        return projections


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Generate growth projections for new business launch')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Run in interactive mode (prompt for inputs)')
    parser.add_argument('--spend', type=float, help='Monthly ad spend')
    parser.add_argument('--aov', type=float, help='Average order value')
    parser.add_argument('--cpc', type=float, help='Cost per click')
    parser.add_argument('--cr', type=float, help='Conversion rate (percent)')
    parser.add_argument('--months', type=int, default=6, help='Months to project')

    args = parser.parse_args()

    projector = GrowthProjector(args.config)

    if args.interactive:
        projector.run_interactive()
    elif args.spend and args.aov:
        # Run with CLI arguments
        projections = projector.generate_projections(
            monthly_ad_spend=args.spend,
            aov=args.aov,
            cpc=args.cpc,
            conversion_rate=args.cr,
            months=args.months
        )
        projector.print_projection_table(projections)
        projector.save_projections(projections)
    else:
        # Run from config
        projector.run_from_config()


if __name__ == '__main__':
    main()
