import zipfile
import xml.etree.ElementTree as ET
import os
import glob

def docx_to_txt(docx_path):
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read('word/document.xml')
        root = ET.fromstring(xml_content)
        paragraphs = []
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        for p in root.findall('.//w:p', ns):
            texts = p.findall('.//w:t', ns)
            if texts:
                paragraphs.append(''.join([t.text for t in texts if t.text]))
            else:
                paragraphs.append('')
        return '\n'.join(paragraphs)
    except Exception as e:
        return f"Error reading {docx_path}: {str(e)}"

def main():
    base_dir = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge"
    
    for filename in os.listdir(base_dir):
        if filename.endswith(".docx"):
            docx_path = os.path.join(base_dir, filename)
            print(f"Parsing {docx_path}...")
            txt_content = docx_to_txt(docx_path)
            txt_path = docx_path.replace(".docx", ".txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(txt_content)
            print(f"Saved to {txt_path}")

if __name__ == "__main__":
    main()
