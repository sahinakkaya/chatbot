#!/usr/bin/env python3
"""
Convert resume-data.json to a well-formatted text file for RAG.

This script reads the structured JSON resume and outputs natural language
text that's optimized for semantic search and question answering.
"""

import json
import sys
from pathlib import Path


def json_to_text(json_path: str, output_path: str) -> None:
    """Convert resume JSON to natural language text file."""

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    lines = []

    # Personal Information
    if "personal" in data:
        lines.append("# PERSONAL INFORMATION")
        lines.append("")

        personal = data["personal"]
        if "name" in personal:
            lines.append(f"Name: {personal['name']}")
            lines.append(f"His name is {personal['name']}.")

        if "title" in personal:
            lines.append(f"Job Title: {personal['title']}")
            lines.append(f"He is a {personal['title']}.")

        if "location" in personal:
            lines.append(f"Location: {personal['location']}")
            lines.append(f"He is located in {personal['location']}. He lives in {personal['location']}.")

        if "email" in personal:
            lines.append(f"Email: {personal['email']}")

        if "website" in personal:
            lines.append(f"Website: {personal['website']}")

        if "github" in personal:
            lines.append(f"GitHub: {personal['github']}")

        if "linkedin" in personal:
            lines.append(f"LinkedIn: {personal['linkedin']}")

        if "stackoverflow" in personal:
            lines.append(f"Stack Overflow: {personal['stackoverflow']}")

        lines.append("")

    # About
    if "about" in data:
        lines.append("# ABOUT")
        lines.append("")
        lines.append(data["about"])
        lines.append("")

    # Summary
    if "summary" in data:
        lines.append("# SUMMARY")
        lines.append("")
        lines.append(data["summary"])
        lines.append("")

    # Education
    if "education" in data:
        lines.append("# EDUCATION")
        lines.append("")

        for edu in data["education"]:
            parts = []

            school = edu.get("school", "")
            degree = edu.get("degree", "")
            duration = edu.get("duration", "")
            location = edu.get("location", "")
            gpa = edu.get("gpa", "")
            courses = edu.get("courses", "")

            if school and degree:
                parts.append(f"He graduated from {school} with a {degree}")
            elif school:
                parts.append(f"He studied at {school}")

            if duration:
                parts.append(f"from {duration}")

            if location:
                parts.append(f"in {location}")

            if gpa:
                parts.append(f"with a GPA of {gpa}")

            text = " ".join(parts) + "."
            lines.append(text)

            if courses:
                lines.append(f"Relevant courses: {courses}.")

            lines.append("")

    # Work Experience
    if "experience" in data:
        lines.append("# WORK EXPERIENCE")
        lines.append("")

        for exp in data["experience"]:
            title = exp.get("title", "")
            company = exp.get("company", "")
            duration = exp.get("duration", "")
            location = exp.get("location", "")
            work_type = exp.get("type", "")
            technologies = exp.get("technologies", "")
            description = exp.get("description", "")
            website = exp.get("website", "")

            # Job header
            if title and company:
                lines.append(f"## {title} at {company}")
                lines.append("")
                lines.append(f"He worked as a {title} at {company}.")

            if duration:
                lines.append(f"Duration: {duration}.")

            if location:
                lines.append(f"Location: {location}.")

            if work_type:
                lines.append(f"Type: {work_type}.")

            if website:
                lines.append(f"Company website: {website}.")

            if technologies:
                lines.append(f"Technologies used: {technologies}.")

            if description:
                lines.append("")
                lines.append(description)

            lines.append("")

    # Skills
    if "skills" in data:
        lines.append("# SKILLS")
        lines.append("")

        skills = data["skills"]

        if "languages" in skills:
            langs = ", ".join(skills["languages"])
            lines.append(f"Programming Languages: {langs}")
            lines.append(f"He is proficient in {langs}.")
            lines.append("")

        if "frameworks" in skills:
            frameworks = ", ".join(skills["frameworks"])
            lines.append(f"Frameworks: {frameworks}")
            lines.append(f"He has experience with {frameworks}.")
            lines.append("")

        if "technologies" in skills:
            tech = ", ".join(skills["technologies"])
            lines.append(f"Technologies: {tech}")
            lines.append(f"He uses {tech}.")
            lines.append("")

        if "concepts" in skills:
            concepts = ", ".join(skills["concepts"])
            lines.append(f"Concepts: {concepts}")
            lines.append(f"He has expertise in {concepts}.")
            lines.append("")

    # Projects
    if "projects" in data:
        lines.append("# PROJECTS")
        lines.append("")

        for proj in data["projects"]:
            name = proj.get("name", "")
            description = proj.get("description", "")
            technologies = proj.get("technologies", "")
            project_type = proj.get("type", "")
            link = proj.get("link", "")

            if name:
                lines.append(f"## {name}")
                lines.append("")

            if project_type:
                lines.append(f"Type: {project_type}")

            if description:
                lines.append(description)

            if technologies:
                if isinstance(technologies, list):
                    tech_str = ", ".join(technologies)
                else:
                    tech_str = technologies
                lines.append(f"Technologies: {tech_str}")

            if link:
                lines.append(f"Link: {link}")

            lines.append("")

    # Interests
    if "interests" in data:
        lines.append("# INTERESTS")
        lines.append("")

        interests = data["interests"]
        if isinstance(interests, list):
            for interest in interests:
                lines.append(f"- {interest}")
        else:
            lines.append(interests)

        lines.append("")

    # Additional Info
    if "additional_info" in data:
        lines.append("# ADDITIONAL INFORMATION")
        lines.append("")

        info = data["additional_info"]
        for key, value in info.items():
            lines.append(f"{key.replace('_', ' ').title()}: {value}")
            lines.append("")

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"✓ Converted {json_path} to {output_path}")
    print(f"✓ Generated {len(lines)} lines of text")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        json_path = "data/resume-data.json"
        output_path = "data/resume-data.txt"
    elif len(sys.argv) < 3:
        json_path = sys.argv[1]
        output_path = json_path.replace('.json', '.txt')
    else:
        json_path = sys.argv[1]
        output_path = sys.argv[2]

    if not Path(json_path).exists():
        print(f"Error: {json_path} not found")
        sys.exit(1)

    json_to_text(json_path, output_path)
