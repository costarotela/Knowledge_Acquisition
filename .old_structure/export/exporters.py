"""
Data export system for knowledge acquisition results.
"""
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import json
import yaml
from datetime import datetime
import asyncio
import aiofiles
from pathlib import Path
import xlsxwriter
import jinja2
import pdfkit
import boto3
import azure.storage.blob
from google.cloud import storage

class BaseExporter:
    """Base class for data exporters."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize exporter."""
        self.config = config
        self.export_path = Path(config.get("export_path", "exports"))
        self.export_path.mkdir(parents=True, exist_ok=True)
    
    async def export(self, data: Any, **kwargs) -> str:
        """Export data to file."""
        raise NotImplementedError

class CSVExporter(BaseExporter):
    """CSV data exporter."""
    
    async def export(self, data: pd.DataFrame, **kwargs) -> str:
        """Export DataFrame to CSV."""
        filename = kwargs.get("filename", f"export_{datetime.now():%Y%m%d_%H%M%S}.csv")
        filepath = self.export_path / filename
        
        # Export with proper encoding and format
        await asyncio.to_thread(
            data.to_csv,
            filepath,
            index=kwargs.get("include_index", False),
            encoding="utf-8"
        )
        
        return str(filepath)

class JSONExporter(BaseExporter):
    """JSON data exporter."""
    
    async def export(self, data: Union[Dict, List], **kwargs) -> str:
        """Export data to JSON."""
        filename = kwargs.get("filename", f"export_{datetime.now():%Y%m%d_%H%M%S}.json")
        filepath = self.export_path / filename
        
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False,
                    default=str
                )
            )
        
        return str(filepath)

class ExcelExporter(BaseExporter):
    """Excel data exporter."""
    
    async def export(self, data: Dict[str, pd.DataFrame], **kwargs) -> str:
        """Export multiple DataFrames to Excel sheets."""
        filename = kwargs.get("filename", f"export_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        filepath = self.export_path / filename
        
        # Create Excel writer
        writer = pd.ExcelWriter(
            filepath,
            engine="xlsxwriter"
        )
        
        # Write each DataFrame to a sheet
        for sheet_name, df in data.items():
            await asyncio.to_thread(
                df.to_excel,
                writer,
                sheet_name=sheet_name,
                index=kwargs.get("include_index", False)
            )
            
            # Auto-adjust columns width
            worksheet = writer.sheets[sheet_name]
            for i, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                worksheet.set_column(i, i, max_length + 2)
        
        writer.close()
        return str(filepath)

class PDFExporter(BaseExporter):
    """PDF report exporter."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize PDF exporter."""
        super().__init__(config)
        self.template_path = Path(config.get("template_path", "templates"))
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_path))
        )
    
    async def export(self, data: Dict[str, Any], **kwargs) -> str:
        """Export data to PDF report."""
        filename = kwargs.get("filename", f"report_{datetime.now():%Y%m%d_%H%M%S}.pdf")
        filepath = self.export_path / filename
        
        # Get template
        template_name = kwargs.get("template", "report_template.html")
        template = self.template_env.get_template(template_name)
        
        # Render HTML
        html = template.render(**data)
        
        # Convert to PDF
        await asyncio.to_thread(
            pdfkit.from_string,
            html,
            str(filepath),
            options={
                "enable-local-file-access": None,
                "quiet": None
            }
        )
        
        return str(filepath)

class CloudExporter:
    """Cloud storage exporter."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize cloud exporter."""
        self.config = config
        self.provider = config.get("provider", "aws").lower()
        
        if self.provider == "aws":
            self.client = boto3.client(
                "s3",
                aws_access_key_id=config["aws_access_key"],
                aws_secret_access_key=config["aws_secret_key"]
            )
            self.bucket = config["aws_bucket"]
            
        elif self.provider == "azure":
            connection_string = config["azure_connection_string"]
            self.client = azure.storage.blob.BlobServiceClient.from_connection_string(
                connection_string
            )
            self.container = self.client.get_container_client(
                config["azure_container"]
            )
            
        elif self.provider == "gcp":
            self.client = storage.Client.from_service_account_json(
                config["gcp_credentials_path"]
            )
            self.bucket = self.client.bucket(config["gcp_bucket"])
            
        else:
            raise ValueError(f"Unsupported cloud provider: {self.provider}")
    
    async def upload(self, filepath: str, **kwargs) -> str:
        """Upload file to cloud storage."""
        filename = Path(filepath).name
        cloud_path = kwargs.get("cloud_path", "")
        
        if cloud_path:
            destination = f"{cloud_path}/{filename}"
        else:
            destination = filename
        
        if self.provider == "aws":
            await asyncio.to_thread(
                self.client.upload_file,
                filepath,
                self.bucket,
                destination
            )
            return f"s3://{self.bucket}/{destination}"
            
        elif self.provider == "azure":
            blob_client = self.container.get_blob_client(destination)
            async with aiofiles.open(filepath, "rb") as f:
                data = await f.read()
                await asyncio.to_thread(
                    blob_client.upload_blob,
                    data,
                    overwrite=True
                )
            return blob_client.url
            
        else:  # GCP
            blob = self.bucket.blob(destination)
            await asyncio.to_thread(
                blob.upload_from_filename,
                filepath
            )
            return f"gs://{self.bucket.name}/{destination}"

class ExportManager:
    """Manager for data exports."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize export manager."""
        self.config = config
        self.exporters = {
            "csv": CSVExporter(config),
            "json": JSONExporter(config),
            "excel": ExcelExporter(config),
            "pdf": PDFExporter(config)
        }
        
        if config.get("cloud_enabled"):
            self.cloud_exporter = CloudExporter(config)
        else:
            self.cloud_exporter = None
    
    async def export(
        self,
        data: Any,
        format: str,
        cloud_upload: bool = False,
        **kwargs
    ) -> Dict[str, str]:
        """Export data to specified format."""
        if format not in self.exporters:
            raise ValueError(f"Unsupported format: {format}")
        
        # Export to file
        filepath = await self.exporters[format].export(data, **kwargs)
        
        result = {"local_path": filepath}
        
        # Upload to cloud if requested
        if cloud_upload and self.cloud_exporter:
            cloud_url = await self.cloud_exporter.upload(filepath, **kwargs)
            result["cloud_url"] = cloud_url
        
        return result
    
    async def export_multiple(
        self,
        data: Any,
        formats: List[str],
        cloud_upload: bool = False,
        **kwargs
    ) -> Dict[str, Dict[str, str]]:
        """Export data to multiple formats."""
        results = {}
        
        for format in formats:
            try:
                result = await self.export(
                    data,
                    format,
                    cloud_upload,
                    **kwargs
                )
                results[format] = result
            except Exception as e:
                results[format] = {"error": str(e)}
        
        return results
