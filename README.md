# Salesforce ERD Generator

This directory contains tools for generating Entity Relationship Diagrams (ERDs) from Salesforce Metadata.

## Overview

The ERD generator parses Salesforce object metadata and creates Mermaid diagrams that follow the established styling standards found in the project documentation. It supports:

- **Standard Objects**: Salesforce standard objects (Account, Contact, etc.)
- **Custom Objects**: Project-specific custom objects (ending in `__c`)
- **Managed Package Objects**: Objects from installed managed packages
- **Relationships**: Master-Detail and Lookup relationships between objects

## Features

- **Comprehensive ERD**: System-wide diagram showing all major objects and relationships
- **Individual Object Diagrams**: Focused diagrams for specific objects and their immediate relationships
- **Object Summary**: Detailed summary of all objects, their types, and relationships
- **Salesforce Styling**: Follows the established color coding and styling standards:
  - Standard Objects: Blue (`#D6E9FF`)
  - Custom Objects: Yellow (`#FFF4C2`)
  - Managed Objects: Orange (`#FFD8B2`)
  - Main Objects: Red (`#FFB3B3`)

## Usage

### Prerequisites

The script uses the existing Python environment in `scripts/erd_env/` which includes the `erdantic` package.

### Basic Usage

```bash
# Generate all ERD diagrams
python generate_erd.py

# Generate diagram for specific objects
python generate_erd.py --objects Account Contact Service_Assignment__c

# Generate diagram for a single object
python generate_erd.py --single-object Service_Assignment__c

# Limit comprehensive ERD to top 30 objects
python generate_erd.py --max-objects 30
```

### Command Line Options

- `--objects-path`: Path to Salesforce objects directory (default: `force-app/main/default/objects`)
- `--output-dir`: Output directory for generated diagrams (default: `ERD`)
- `--objects`: Specific objects to include (default: all)
- `--max-objects`: Maximum number of objects in comprehensive ERD (default: 50)
- `--single-object`: Generate diagram for a single object only

### Output Files

The generator creates several output files:

1. **`comprehensive_erd.md`**: System-wide ERD showing the most connected objects
2. **`{object_name}_erd.md`**: Individual diagrams for top 20 most connected objects
3. **`object_summary.md`**: Detailed summary of all objects and relationships

## Example Output

### Mermaid Diagram Structure

```mermaid
graph TD
Account["Account"]:::object
Contact["Contact"]:::object
Service_Assignment__c["Service Assignment"]:::customObject

Account -->|Service Assignment| Service_Assignment__c
Contact -->|Person Being Served| Service_Assignment__c

classDef object fill:#D6E9FF,stroke:#0070D2,stroke-width:3px,rx:12px,ry:12px,shadow:drop,color:#333;
classDef customObject fill:#FFF4C2,stroke:#CCAA00,stroke-width:3px,rx:12px,ry:12px,shadow:drop,color:#333;
classDef customObjectManaged fill:#FFD8B2,stroke:#CC5500,stroke-width:3px,rx:12px,ry:12px,shadow:drop,color:#333;
classDef mainObject fill:#FFB3B3,stroke:#A94442,stroke-width:4px,rx:14px,ry:14px,shadow:drop,color:#333,font-weight:bold;

linkStyle stroke:#A6A6A6,stroke-width:2px;
```

## Object Types and Styling

| Object Type | Color | Usage |
|-------------|-------|-------|
| Standard Objects | Blue (`#D6E9FF`) | Salesforce standard objects like Account, Contact |
| Custom Objects | Yellow (`#FFF4C2`) | Project-specific custom objects ending in `__c` |
| Managed Objects | Orange (`#FFD8B2`) | Objects from installed managed packages |
| Main Objects | Red (`#FFB3B3`) | Primary objects in specific diagrams |

## Relationship Types

- **Master-Detail**: Strong parent-child relationships (solid arrows)
- **Lookup**: Reference relationships (solid arrows)

## Integration with Documentation

The generated diagrams follow the same styling standards used in the existing project documentation found in the `docs/` directory. They can be easily integrated into:

- Markdown documentation files
- Mermaid-compatible viewers
- GitHub/GitLab documentation
- Confluence or other documentation platforms

## Troubleshooting

### Common Issues

1. **No objects found**: Check that the `--objects-path` points to the correct Salesforce objects directory
2. **Permission errors**: Ensure the script has read access to the objects directory
3. **Missing relationships**: Some relationships may not be captured if referenced objects are not included in the analysis

### Performance Considerations

- Large orgs with many objects may take time to process
- Use `--max-objects` to limit the comprehensive ERD size
- Use `--objects` to focus on specific objects of interest

## Contributing

When modifying the ERD generator:

1. Maintain compatibility with existing styling standards
2. Test with various object types and relationship configurations
3. Update this README if adding new features
4. Ensure generated diagrams are readable and follow Salesforce conventions

## Related Files

- `generate_erd.py`: Main ERD generation script
- `scripts/erd_env/`: Python environment with required dependencies
- `docs/objects/`: Existing object documentation with ERD examples
- `force-app/main/default/objects/`: Salesforce object metadata source
