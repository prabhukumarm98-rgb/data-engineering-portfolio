"""
Production Monitoring Dashboard for Data Pipelines
Tracks: Pipeline health, data quality, costs, and performance
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
import json


class PipelineMonitor:
    """
    Production monitoring dashboard used by data engineering teams
    Tracks 50+ pipelines in real-time
    """
    
    def __init__(self):
        st.set_page_config(
            page_title="Data Pipeline Dashboard",
            page_icon="",
            layout="wide"
        )
        
        self.sla_targets = {
            "data_freshness": 60,  # minutes
            "pipeline_success_rate": 99.9,  # percentage
            "cost_per_tb": 23.00,  # dollars
            "error_rate": 0.1,  # percentage
        }
    
    def get_pipeline_metrics(self):
        """Fetch pipeline metrics from monitoring system"""
        # In production, this would query Prometheus/CloudWatch
        return {
            "total_pipelines": 52,
            "active_pipelines": 48,
            "failed_today": 2,
            "avg_execution_time": "45.2m",
            "data_processed_today": "15.2TB",
            "total_cost_today": "$342.18",
            "sla_compliance": 99.7,
        }
    
    def get_recent_alerts(self):
        """Get recent pipeline alerts"""
        return [
            {
                "pipeline": "user_behavior_etl",
                "severity": "HIGH",
                "message": "Data freshness > 2 hours",
                "timestamp": "2024-01-15 10:30:00",
                "status": "OPEN"
            },
            {
                "pipeline": "transaction_processing",
                "severity": "MEDIUM",
                "message": "Row count dropped by 30%",
                "timestamp": "2024-01-15 09:15:00",
                "status": "INVESTIGATING"
            },
            {
                "pipeline": "data_quality_checks",
                "severity": "LOW",
                "message": "5 null values in customer_email",
                "timestamp": "2024-01-15 08:45:00",
                "status": "RESOLVED"
            }
        ]
    
    def get_cost_data(self):
        """Get cost breakdown by pipeline"""
        return pd.DataFrame({
            "pipeline": [
                "real_time_analytics", "batch_etl", "ml_training", 
                "data_quality", "reporting", "backup"
            ],
            "daily_cost": [125.50, 89.75, 67.30, 23.45, 18.90, 17.28],
            "data_processed_tb": [5.2, 3.8, 2.1, 0.8, 1.5, 1.8],
            "cost_per_tb": [24.13, 23.62, 32.05, 29.31, 12.60, 9.60]
        })
    
    def get_performance_trends(self):
        """Get performance trends over time"""
        dates = pd.date_range(start='2024-01-01', end='2024-01-15', freq='D')
        
        return pd.DataFrame({
            "date": dates,
            "success_rate": [99.8, 99.9, 99.7, 99.9, 99.8, 99.6, 99.9,
                             99.8, 99.9, 99.7, 99.8, 99.9, 99.8, 99.7, 99.9],
            "avg_latency_minutes": [42, 38, 45, 39, 41, 47, 40,
                                    38, 36, 44, 39, 37, 42, 45, 38],
            "data_volume_tb": [12.5, 13.2, 11.8, 14.1, 13.5, 12.9, 13.8,
                               14.2, 13.9, 12.7, 14.5, 13.8, 12.9, 13.5, 14.1],
            "cost_usd": [285, 302, 278, 315, 298, 290, 308,
                         320, 312, 284, 325, 310, 295, 305, 318]
        })
    
    def create_metrics_cards(self):
        """Create summary metrics cards"""
        metrics = self.get_pipeline_metrics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Pipelines",
                value=metrics["total_pipelines"],
                delta=f"{metrics['active_pipelines']} active"
            )
        
        with col2:
            success_color = "normal" if metrics["sla_compliance"] >= 99.9 else "off"
            st.metric(
                label="SLA Compliance",
                value=f"{metrics['sla_compliance']}%",
                delta="0.2% from target",
                delta_color=success_color
            )
        
        with col3:
            st.metric(
                label="Data Processed Today",
                value=metrics["data_processed_today"],
                delta="+2.1TB from yesterday"
            )
        
        with col4:
            st.metric(
                label="Total Cost Today",
                value=metrics["total_cost_today"],
                delta="-$18.42 vs budget"
            )
    
    def create_alerts_section(self):
        """Display recent alerts"""
        st.subheader("Recent Alerts")
        
        alerts = self.get_recent_alerts()
        
        for alert in alerts:
            severity_color = {
                "HIGH": "red",
                "MEDIUM": "orange",
                "LOW": "yellow"
            }.get(alert["severity"], "gray")
            
            with st.expander(
                f"{alert['severity']}: {alert['pipeline']} - {alert['message']}",
                expanded=alert["severity"] == "HIGH"
            ):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Pipeline:** {alert['pipeline']}")
                
                with col2:
                    st.write(f"**Time:** {alert['timestamp']}")
                
                with col3:
                    status_color = "green" if alert["status"] == "RESOLVED" else "red"
                    st.write(f"**Status:** :{status_color}[{alert['status']}]")
    
    def create_performance_charts(self):
        """Create performance trend charts"""
        st.subheader("Performance Trends")
        
        trends = self.get_performance_trends()
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Success Rate %", "Average Latency (minutes)",
                          "Data Volume (TB)", "Daily Cost ($)"),
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )
        
        # Success Rate
        fig.add_trace(
            go.Scatter(
                x=trends["date"],
                y=trends["success_rate"],
                mode="lines+markers",
                name="Success Rate",
                line=dict(color="green", width=2)
            ),
            row=1, col=1
        )
        
        # Add SLA target line
        fig.add_hline(
            y=self.sla_targets["pipeline_success_rate"],
            line_dash="dash",
            line_color="red",
            row=1, col=1,
            annotation_text="SLA Target"
        )
        
        # Average Latency
        fig.add_trace(
            go.Scatter(
                x=trends["date"],
                y=trends["avg_latency_minutes"],
                mode="lines+markers",
                name="Avg Latency",
                line=dict(color="blue", width=2)
            ),
            row=1, col=2
        )
        
        # Data Volume
        fig.add_trace(
            go.Bar(
                x=trends["date"],
                y=trends["data_volume_tb"],
                name="Data Volume",
                marker_color="orange"
            ),
            row=2, col=1
        )
        
        # Daily Cost
        fig.add_trace(
            go.Scatter(
                x=trends["date"],
                y=trends["cost_usd"],
                mode="lines+markers",
                name="Daily Cost",
                line=dict(color="purple", width=2),
                fill="tozeroy"
            ),
            row=2, col=2
        )
        
        # Add budget line
        fig.add_hline(
            y=300,
            line_dash="dash",
            line_color="red",
            row=2, col=2,
            annotation_text="Budget"
        )
        
        fig.update_layout(
            height=600,
            showlegend=False,
            title_text="Pipeline Performance Metrics (Last 15 Days)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def create_cost_analysis(self):
        """Create cost breakdown analysis"""
        st.subheader("Cost Analysis")
        
        cost_data = self.get_cost_data()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Cost breakdown pie chart
            fig = go.Figure(data=[go.Pie(
                labels=cost_data["pipeline"],
                values=cost_data["daily_cost"],
                hole=0.3,
                textinfo="label+percent",
                marker=dict(colors=px.colors.sequential.Viridis)
            )])
            
            fig.update_layout(
                title="Daily Cost Breakdown by Pipeline",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Cost efficiency bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=cost_data["pipeline"],
                y=cost_data["cost_per_tb"],
                name="Cost per TB",
                marker_color=cost_data["cost_per_tb"].apply(
                    lambda x: "green" if x < self.sla_targets["cost_per_tb"] else "red"
                )
            ))
            
            fig.add_hline(
                y=self.sla_targets["cost_per_tb"],
                line_dash="dash",
                line_color="red",
                annotation_text="Target"
            )
            
            fig.update_layout(
                title="Cost Efficiency (Lower is Better)",
                yaxis_title="Cost per TB ($)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Cost optimization recommendations
        st.subheader("Optimization Recommendations")
        
        expensive_pipelines = cost_data[
            cost_data["cost_per_tb"] > self.sla_targets["cost_per_tb"]
        ]
        
        if len(expensive_pipelines) > 0:
            st.warning(f"**{len(expensive_pipelines)} pipelines exceeding cost target:**")
            
            for _, row in expensive_pipelines.iterrows():
                st.write(f"""
                - **{row['pipeline']}**: ${row['cost_per_tb']:.2f}/TB 
                  (${row['cost_per_tb'] - self.sla_targets['cost_per_tb']:.2f} above target)
                  *Recommendation: Review partitioning strategy and consider data compression*
                """)
        else:
            st.success("All pipelines within cost targets!")
    
    def create_sla_monitoring(self):
        """Create SLA monitoring section"""
        st.subheader("SLA Monitoring")
        
        # Simulated SLA metrics
        sla_data = pd.DataFrame({
            "Metric": ["Data Freshness", "Pipeline Success", "Error Rate", "Cost Efficiency"],
            "Current": [55, 99.7, 0.15, 22.50],
            "Target": [60, 99.9, 0.10, 23.00],
            "Unit": ["minutes", "%", "%", "$/TB"]
        })
        
        # Calculate status
        sla_data["Status"] = sla_data.apply(
            lambda row: "MET" if row["Current"] <= row["Target"] else "⚠️ MISSING",
            axis=1
        )
        
        # Display as table
        st.dataframe(
            sla_data.style.apply(
                lambda x: ["background-color: #d4edda" if x["Status"] == "MET" 
                          else "background-color: #f8d7da" for _ in x],
                axis=1
            ),
            use_container_width=True
        )
        
        # SLA compliance trend
        st.write("**SLA Compliance Trend:**")
        
        compliance_trend = pd.DataFrame({
            "Week": ["W1", "W2", "W3", "W4"],
            "Compliance": [98.5, 99.2, 99.5, 99.7]
        })
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=compliance_trend["Week"],
            y=compliance_trend["Compliance"],
            mode="lines+markers+text",
            text=compliance_trend["Compliance"],
            textposition="top center",
            line=dict(color="green", width=3),
            marker=dict(size=10)
        ))
        
        fig.add_hline(
            y=99.0,
            line_dash="dash",
            line_color="orange",
            annotation_text="Minimum Target"
        )
        
        fig.update_layout(
            title="Weekly SLA Compliance Trend",
            yaxis_title="Compliance %",
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def run_dashboard(self):
        """Main dashboard execution"""
        st.title("Data Pipeline Monitoring Dashboard")
        st.markdown("Real-time monitoring of 50+ production data pipelines")
        
        # Sidebar filters
        with st.sidebar:
            st.header("Filters")
            
            environment = st.selectbox(
                "Environment",
                ["All", "Production", "Staging", "Development"]
            )
            
            date_range = st.date_input(
                "Date Range",
                value=[datetime.now() - timedelta(days=7), datetime.now()]
            )
            
            severity_filter = st.multiselect(
                "Alert Severity",
                ["HIGH", "MEDIUM", "LOW"],
                default=["HIGH", "MEDIUM"]
            )
            
            st.divider()
            
            st.markdown("**Last Updated:**")
            st.code(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if st.button("Refresh Data", type="primary"):
                st.rerun()
        
        # Dashboard sections
        self.create_metrics_cards()
        
        st.divider()
        
        self.create_alerts_section()
        
        st.divider()
        
        self.create_performance_charts()
        
        st.divider()
        
        self.create_cost_analysis()
        
        st.divider()
        
        self.create_sla_monitoring()
        
        # Footer
        st.divider()
        st.caption("""
        **Monitoring Stack:** Prometheus + Grafana + CloudWatch + Custom Metrics  
        **Alerting:** PagerDuty + Slack + Email  
        **Data Sources:** Airflow, Spark, Snowflake, AWS Cost Explorer  
        **Refresh Rate:** 5 minutes | **Data Lag:** < 60 seconds
        """)


# Run the dashboard
if __name__ == "__main__":
    monitor = PipelineMonitor()
    monitor.run_dashboard()
