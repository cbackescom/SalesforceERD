#!/usr/bin/env python3
"""
Salesforce ERD Generator using DOT (Graphviz)
Generates Entity-Relationship Diagrams for Salesforce objects using DOT notation.
"""

import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import subprocess

# Constants and Configuration
class ERDConfig:
    """Configuration constants for ERD generation."""
    
    # Default values
    DEFAULT_MAX_OBJECTS = 15
    DEFAULT_WIDTH = 2500
    DEFAULT_FILENAME = "final_erd"
    DEFAULT_ENGINE = "dot"
    DEFAULT_FORMATS = ["svg"]
    
    # Field limiting thresholds
    FIELD_LIMIT_THRESHOLDS = {
        500: 2,   # Very restrictive for massive diagrams
        200: 3,   # Restrictive for large diagrams
        100: 4,   # Moderate limit for medium diagrams
        50: 6,    # Light limit for medium diagrams
        20: 8,    # Light limit for smaller diagrams
    }
    
    # Object colors (Salesforce ERD standards)
    COLORS = {
        'standard': "#E1F5FE",  # Light blue for standard objects
        'managed': "#FFE0B2",   # Light orange for managed package objects
        'custom': "#FFF9C4",    # Light yellow for custom objects
    }
    
    # DOT styling
    DOT_STYLES = {
        'title_fontsize': 24,
        'node_fontsize': 12,
        'edge_fontsize': 10,
        'node_margin': 0.1,
        'node_sep': 1.0,
        'rank_sep': 2.0,
        'edge_penwidth': 1.5,
        'master_detail_penwidth': 2.0,
        'font_family': "Arial, sans-serif",
    }
    
    # Relationship arrow styles
    ARROW_STYLES = {
        'master_detail': "arrowhead=dot, arrowtail=dot, color=steelblue, penwidth=2.0",
        'lookup': "arrowhead=open, arrowtail=none, color=gray, penwidth=1.5",
    }
    
    # Display limits
    MAX_OBJECTS_DISPLAY = 10  # Max objects to show in selection message


@dataclass
class SalesforceField:
    name: str
    type: str
    required: bool = False
    is_lookup: bool = False
    reference_to: Optional[str] = None


@dataclass
class SalesforceObject:
    name: str
    label: str
    fields: List[SalesforceField]
    is_standard: bool = False
    is_managed: bool = False


@dataclass
class Relationship:
    from_object: str
    to_object: str
    from_field: str
    to_field: str
    type: str  # "Lookup" or "Master-Detail"
    label: str


class SalesforceERDGenerator:
    def __init__(self, objects_path: str, output_dir: str = "output"):
        self.objects_path = Path(objects_path)
        self.output_dir = Path(output_dir)
        self.objects: Dict[str, SalesforceObject] = {}
        self.relationships: List[Relationship] = []
        
        # Ensure output directory structure exists
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)
    
    def load_objects(self, object_names: List[str] = None):
        """Load Salesforce objects from metadata files."""
        if not self.objects_path.exists():
            raise FileNotFoundError(f"Objects path not found: {self.objects_path}")
        
        print("Loading Salesforce objects...")
        
        # Get list of object directories
        object_dirs = [d for d in self.objects_path.iterdir() if d.is_dir()]
        
        # Filter by object names if specified
        if object_names:
            object_dirs = [d for d in object_dirs if d.name in object_names]
        
        for obj_dir in object_dirs:
            obj_name = obj_dir.name
            obj_file = obj_dir / f"{obj_name}.object-meta.xml"
            
            if obj_file.exists():
                try:
                    obj = self._parse_object_metadata(obj_file)
                    if obj:
                        self.objects[obj_name] = obj
                        print(f"Loaded object: {obj_name} ({obj.label})")
                except Exception as e:
                    print(f"Error loading {obj_name}: {e}")
        
        print(f"Loaded {len(self.objects)} objects")
    
    def _parse_object_metadata(self, obj_file: Path) -> Optional[SalesforceObject]:
        """Parse Salesforce object metadata XML file."""
        try:
            tree = ET.parse(obj_file)
            root = tree.getroot()
            
            # Define namespace for Salesforce metadata
            ns = {'sf': 'http://soap.sforce.com/2006/04/metadata'}
            
            # Get object name and label
            name = obj_file.parent.name  # Object name is the directory name
            label_elem = root.find('sf:label', ns)
            label = label_elem.text if label_elem is not None else name
            
            # Determine object type
            is_standard = not name.endswith('__c') and not name.endswith('__mdt')
            is_managed = '__' in name and not name.endswith('__c') and not name.endswith('__mdt')
            
            # Parse fields from the fields directory
            fields = []
            fields_dir = obj_file.parent / 'fields'
            if fields_dir.exists():
                for field_file in fields_dir.glob('*.field-meta.xml'):
                    field = self._parse_field_metadata(field_file)
                    if field:
                        fields.append(field)
            
            return SalesforceObject(
                name=name,
                label=label,
                fields=fields,
                is_standard=is_standard,
                is_managed=is_managed
            )
            
        except Exception as e:
            print(f"Error parsing {obj_file}: {e}")
            return None
    
    def _parse_field_metadata(self, field_file: Path) -> Optional[SalesforceField]:
        """Parse field metadata from XML file."""
        try:
            tree = ET.parse(field_file)
            root = tree.getroot()
            
            # Define namespace for Salesforce metadata
            ns = {'sf': 'http://soap.sforce.com/2006/04/metadata'}
            
            name_elem = root.find('sf:fullName', ns)
            type_elem = root.find('sf:type', ns)
            required_elem = root.find('sf:required', ns)
            reference_to_elem = root.find('sf:referenceTo', ns)
            
            if name_elem is None or type_elem is None:
                return None
            
            name = name_elem.text
            field_type = type_elem.text
            required = required_elem is not None and required_elem.text == 'true'
            is_lookup = field_type in ['Lookup', 'MasterDetail']
            reference_to = reference_to_elem.text if reference_to_elem is not None else None
            
            return SalesforceField(
                name=name,
                type=field_type,
                required=required,
                is_lookup=is_lookup,
                reference_to=reference_to
            )
            
        except Exception as e:
            return None
    
    def build_relationships(self):
        """Build relationships between objects based on lookup fields."""
        print("Building relationships...")
        
        for obj_name, obj in self.objects.items():
            for field in obj.fields:
                if field.is_lookup and field.reference_to:
                    # Create relationship
                    rel_type = "Master-Detail" if field.type == "MasterDetail" else "Lookup"
                    rel = Relationship(
                        from_object=obj_name,
                        to_object=field.reference_to,
                        from_field=field.name,
                        to_field="Id",  # Standard relationship field
                        type=rel_type,
                        label=field.name
                    )
                    self.relationships.append(rel)
        
        print(f"Found {len(self.relationships)} relationships")
    
    def get_key_fields(self, obj: SalesforceObject) -> List[SalesforceField]:
        """Get only relationship fields (lookup and master-detail) that connect to other entities."""
        relationship_fields = []
        
        # Only include lookup and master-detail fields that have a reference_to value
        for field in obj.fields:
            if field.is_lookup and field.reference_to:
                relationship_fields.append(field)
        
        return relationship_fields
    
    def get_top_connected_objects(self, max_objects: int) -> List[str]:
        """Get top objects by relationship count."""
        object_counts = {}
        
        for rel in self.relationships:
            object_counts[rel.from_object] = object_counts.get(rel.from_object, 0) + 1
            object_counts[rel.to_object] = object_counts.get(rel.to_object, 0) + 1
        
        # Sort by relationship count
        sorted_objects = sorted(object_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [obj_name for obj_name, count in sorted_objects[:max_objects]]
    
    def sanitize_label(self, label: str) -> str:
        """Sanitize label for DOT format."""
        # Remove or replace problematic characters
        label = label.replace('"', '\\"')
        label = label.replace('\n', ' ')
        label = label.replace('\r', ' ')
        label = label.replace('|', '\\|')
        
        # Limit length to prevent parsing issues (shorter for better readability)
        if len(label) > 25:
            label = label[:22] + "..."
        return label
    
    def generate_dot_erd(self, objects: List[str], title: str = "Salesforce ERD", show_fields: bool = True, max_fields_per_entity: int = None) -> str:
        """Generate a DOT (Graphviz) ERD diagram."""
        dot_lines = [
            "digraph G {",
            f'  label="{title}";',
            "  labelloc=t;",
            f"  fontsize={ERDConfig.DOT_STYLES['title_fontsize']};",
            f"  fontname=\"{ERDConfig.DOT_STYLES['font_family']}\";",
            "  rankdir=LR;",  # Left to right layout for better horizontal space usage
            "  splines=ortho;",  # Use orthogonal (straight) lines for cleaner look
            f"  nodesep={ERDConfig.DOT_STYLES['node_sep']};",    # Spacing between nodes
            f"  ranksep={ERDConfig.DOT_STYLES['rank_sep']};",    # Spacing between ranks
            "  overlap=false;",  # Prevent node overlap
            "  concentrate=false;",  # Don't merge parallel edges
            f"  node [shape=record, style=filled, fontname=\"{ERDConfig.DOT_STYLES['font_family']}\", fontsize={ERDConfig.DOT_STYLES['node_fontsize']}, margin={ERDConfig.DOT_STYLES['node_margin']}];",
            f"  edge [fontname=\"{ERDConfig.DOT_STYLES['font_family']}\", fontsize={ERDConfig.DOT_STYLES['edge_fontsize']}, penwidth={ERDConfig.DOT_STYLES['edge_penwidth']}];",
            ""
        ]
        
        # Add nodes (entities)
        for obj_name in objects:
            if obj_name in self.objects:
                obj = self.objects[obj_name]
                
                # Create node label with fields
                if show_fields:
                    # Get fields to display
                    key_fields = self.get_key_fields(obj)
                    if max_fields_per_entity is not None:
                        key_fields = key_fields[:max_fields_per_entity]
                    
                    # Create DOT record format with better readability
                    field_lines = []
                    for field in key_fields:
                        field_name = field.name
                        if field.required:
                            field_name = f"*{field_name}*"  # Use asterisks for required fields instead of HTML
                        # Show full field names for better clarity
                        field_lines.append(f"{field_name} : {field.type}")
                    
                    if max_fields_per_entity is not None and len(self.get_key_fields(obj)) > max_fields_per_entity:
                        field_lines.append(f"... {len(self.get_key_fields(obj)) - max_fields_per_entity} more")
                    
                    # DOT record format: "label|field1|field2|..." with better spacing
                    node_content = f"*{obj.label}*|" + "|".join(field_lines)
                else:
                    node_content = f"*{obj.label}*"
                
                # Add color based on Salesforce ERD standards
                if obj.is_standard:
                    color = ERDConfig.COLORS['standard']
                elif obj.is_managed:
                    color = ERDConfig.COLORS['managed']
                else:
                    color = ERDConfig.COLORS['custom']
                
                dot_lines.append(f'  {obj_name} [label="{node_content}", fillcolor="{color}"];')
        
        dot_lines.append("")
        
        # Add edges (relationships) with field names
        for rel in self.relationships:
            if rel.from_object in objects and rel.to_object in objects:
                # Determine arrow style and color based on relationship type
                if rel.type == "Master-Detail":
                    arrow_style = ERDConfig.ARROW_STYLES['master_detail']
                else:  # Lookup
                    arrow_style = ERDConfig.ARROW_STYLES['lookup']
                
                # Use ports to connect to specific field positions and include field name in the connection
                # This creates a more direct visual connection between the field and the relationship
                dot_lines.append(f'  {rel.from_object}:"{rel.from_field}" -> {rel.to_object} [{arrow_style}];')
        
        dot_lines.append("}")
        
        return "\n".join(dot_lines)
    
    def generate_image_from_dot(self, dot_content: str, output_file: Path, format_type: str, width: int = ERDConfig.DEFAULT_WIDTH, engine: str = ERDConfig.DEFAULT_ENGINE) -> bool:
        """Generate image from DOT content using Graphviz."""
        try:
            # Create temporary DOT file
            temp_dot = self.output_dir / "temp.dot"
            with open(temp_dot, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            
            # Determine output format and Graphviz command
            if format_type == "svg":
                cmd = [engine, "-Tsvg", "-o", str(output_file), str(temp_dot)]
            elif format_type == "png":
                cmd = [engine, "-Tpng", "-Gdpi=300", "-o", str(output_file), str(temp_dot)]
            elif format_type == "pdf":
                cmd = [engine, "-Tpdf", "-o", str(output_file), str(temp_dot)]
            else:
                print(f"Unsupported format for DOT: {format_type}")
                return False
            
            # Run Graphviz
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Clean up temp file
            if temp_dot.exists():
                temp_dot.unlink()
            
            if result.returncode == 0:
                return True
            else:
                print(f"Graphviz error: {result.stderr}")
                return False
                
        except FileNotFoundError:
            print("❌ Graphviz (dot) not found. Please install Graphviz:")
            print("   macOS: brew install graphviz")
            print("   Ubuntu: sudo apt-get install graphviz")
            print("   Windows: Download from https://graphviz.org/download/")
            return False
        except Exception as e:
            print(f"Error generating DOT image: {e}")
            return False

    def generate_erd_with_images(self, max_objects: int = ERDConfig.DEFAULT_MAX_OBJECTS, formats: List[str] = None, filename: str = "salesforce_erd", layout: str = "auto", width: int = ERDConfig.DEFAULT_WIDTH, show_fields: bool = True, max_fields_per_entity: int = None, auto_limit_fields: bool = True, engine: str = ERDConfig.DEFAULT_ENGINE) -> bool:
        """Generate ERD and create images in one go."""
        if formats is None:
            formats = ERDConfig.DEFAULT_FORMATS
        
        print(f"Generating ERD with top {max_objects} objects...")
        
        # Get top connected objects
        top_objects = self.get_top_connected_objects(max_objects)
        if not top_objects:
            print("No objects found to generate ERD")
            return False
        
        print(f"Selected objects: {', '.join(top_objects[:ERDConfig.MAX_OBJECTS_DISPLAY])}{'...' if len(top_objects) > ERDConfig.MAX_OBJECTS_DISPLAY else ''}")
        
        # DOT has label length limits, so we need to be more aggressive with field limiting for readability
        if auto_limit_fields and max_fields_per_entity is None:
            for threshold, limit in ERDConfig.FIELD_LIMIT_THRESHOLDS.items():
                if len(top_objects) >= threshold:
                    max_fields_per_entity = limit
                    print(f"⚠️  Auto-limiting to {limit} fields per entity for readability")
                    break
        
        # Generate DOT ERD
        print("Using DOT (Graphviz) engine for optimal scalability...")
        erd_content = self.generate_dot_erd(top_objects, "Salesforce System ERD", show_fields, max_fields_per_entity)
        
        # Save DOT file
        dot_path = self.output_dir / f"{filename}.dot"
        with open(dot_path, 'w', encoding='utf-8') as f:
            f.write(erd_content)
        print(f"📄 Saved ERD DOT: {dot_path}")
        
        # Generate images
        images_dir = self.output_dir / "images"
        success_count = 0
        
        for format_type in formats:
            output_file = images_dir / f"{filename}.{format_type}"
            if self.generate_image_from_dot(erd_content, output_file, format_type, width, engine):
                print(f"✅ Generated {format_type.upper()}: {output_file}")
                success_count += 1
            else:
                print(f"❌ Failed to generate {format_type.upper()}")
        
        if success_count > 0:
            print(f"\n🎉 ERD generation complete!")
            print(f"✅ Generated {success_count}/{len(formats)} images")
            print(f"📁 Images saved to: {images_dir}")
            return True
        else:
            print("❌ Failed to generate any images")
            return False


def main():
    parser = argparse.ArgumentParser(description="Generate Salesforce ERD using DOT (Graphviz)")
    parser.add_argument("--objects-path",
                       default="../force-app/main/default/objects",
                       help="Path to Salesforce objects directory (default: ../force-app/main/default/objects)")
    parser.add_argument("--output-dir",
                       default="output",
                       help="Output directory for generated files (default: output)")
    parser.add_argument("--max-objects", 
                       type=int,
                       default=ERDConfig.DEFAULT_MAX_OBJECTS,
                       help="Maximum number of objects in ERD")
    parser.add_argument("--formats", 
                       nargs="+",
                       default=ERDConfig.DEFAULT_FORMATS,
                       choices=["png", "svg", "pdf"],
                       help="Image formats to generate (default: svg)")
    parser.add_argument("--filename",
                       default=ERDConfig.DEFAULT_FILENAME,
                       help="Base filename for output files")
    parser.add_argument("--objects", 
                       nargs="*",
                       help="Specific objects to include (default: auto-select top connected)")
    parser.add_argument("--layout",
                       default="auto",
                       choices=["auto", "left-right", "top-down"],
                       help="Layout direction (default: auto)")
    parser.add_argument("--engine",
                       default=ERDConfig.DEFAULT_ENGINE,
                       choices=["dot", "neato", "fdp", "sfdp", "circo", "twopi"],
                       help="Graphviz layout engine: dot (hierarchical), neato (spring), fdp (force-directed), sfdp (scalable force), circo (circular), twopi (radial)")
    parser.add_argument("--width",
                       type=int,
                       default=ERDConfig.DEFAULT_WIDTH,
                       help="Image width in pixels (default: 1200)")
    parser.add_argument("--show-fields",
                       action="store_true",
                       default=True,
                       help="Show fields inside object boxes (default: True)")
    parser.add_argument("--hide-fields",
                       action="store_true",
                       help="Hide fields inside object boxes (simpler view)")
    parser.add_argument("--max-fields-per-entity", type=int, default=None,
                       help="Limit number of fields shown per entity (default: auto-limited for large diagrams)")
    parser.add_argument("--auto-limit-fields", action="store_true", default=True,
                       help="Automatically limit fields for large diagrams to avoid readability issues (default: True)")
    
    args = parser.parse_args()
    
    try:
        # Initialize generator
        generator = SalesforceERDGenerator(args.objects_path, args.output_dir)
        
        # Load objects
        generator.load_objects(args.objects)
        
        if not generator.objects:
            print("No objects found. Please check the objects path.")
            return 1
        
        # Build relationships
        generator.build_relationships()
        
        # Determine if fields should be shown
        show_fields = args.show_fields and not args.hide_fields
        
        # Generate ERD and images
        success = generator.generate_erd_with_images(
            max_objects=args.max_objects,
            formats=args.formats,
            filename=args.filename,
            layout=args.layout,
            width=args.width,
            show_fields=show_fields,
            max_fields_per_entity=args.max_fields_per_entity,
            auto_limit_fields=args.auto_limit_fields,
            engine=args.engine
        )
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
