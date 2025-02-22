import os
import re
import json


class DynamicJSXGenerator:
    def __init__(self, debug_output=False):
        self.debug_output = debug_output

    def generate_jsx_from_template(self, template_name, replacements):
        """
        Generates a JSX script from a template file with the given replacements.

        Args:
            template_name (str): Name of the template file
            replacements (dict): Dictionary containing replacement values

        Returns:
            str: Generated JSX script content
        """
        if isinstance(replacements, str):
            try:
                replacements = json.loads(replacements)
            except:
                replacements = {}

        if not isinstance(replacements, dict):
            replacements = {}

        # Füge debug_output zu den Ersetzungen hinzu
        replacements['DEBUG_OUTPUT'] = str(self.debug_output).lower()

        template_path = os.path.join('jsx_templates', template_name)
        with open(template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()

        # Ersetze den DEBUG_OUTPUT-Block im Template
        template_content = re.sub(
            r'if \(typeof DEBUG_OUTPUT === "undefined"\) \{\s*var DEBUG_OUTPUT = .*?;\s*\}',
            f'var DEBUG_OUTPUT = {replacements["DEBUG_OUTPUT"]};',
            template_content
        )

        # Führe die restlichen Ersetzungen durch
        for key, value in replacements.items():
            if isinstance(value, str):
                # Escape Anführungszeichen in Strings
                value = value.replace('"', '\\"')
            template_content = template_content.replace(f'${{{key}}}', str(value))

        return template_content

    def generate_contentcheck_jsx(self, image_path, check_settings, output_path):
        """
        Generates a JSX script for content checking with the given parameters.

        Args:
            image_path (str): Path to the image file
            check_settings (dict): Dictionary containing check settings
            output_path (str): Path where to save the results

        Returns:
            str: Generated JSX script content
        """
        replacements = {
            'IMAGE_PATH': image_path,
            'CHECK_SETTINGS': str(check_settings),
            'OUTPUT_PATH': output_path
        }

        return self.generate_jsx_from_template('contentcheck_template.jsx', replacements)

    def save_jsx_script(self, jsx_content, output_path):
        """
        Saves the generated JSX script to a file.

        Args:
            jsx_content (str): The JSX script content
            output_path (str): Path where to save the script
        """
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(jsx_content)


def generate_jsx_script(hf_config, file_name, debug_output=False):
    """
    Compatibility function for existing code.

    Args:
        hf_config: Hotfolder configuration
        file_name: Name of the file to process
        debug_output: Boolean for debug output

    Returns:
        str: Path to the generated JSX script
    """
    generator = DynamicJSXGenerator(debug_output=debug_output)

    # Erstelle ein Dictionary mit den Ersetzungen
    replacements = {
        'IMAGE_PATH': file_name,
        'CONFIG': json.dumps(hf_config) if isinstance(hf_config, dict) else str(hf_config)
    }

    # Generiere das JSX-Script
    jsx_content = generator.generate_jsx_from_template('contentcheck_template.jsx', replacements)

    # Speichere das Script
    output_dir = 'temp'
    os.makedirs(output_dir, exist_ok=True)
    jsx_script_path = os.path.join(output_dir, f'generated_script_{os.path.basename(file_name)}.jsx')

    generator.save_jsx_script(jsx_content, jsx_script_path)
    return jsx_script_path