# Repository Guidelines

## Project Structure & Module Organization
- `pageindex/` holds the core library (`page_index.py`, `page_index_md.py`, `utils.py`, and `config.yaml`).
- `run_pageindex.py` is the main CLI entry point for generating a tree index from PDFs or Markdown.
- `cookbook/` and `tutorials/` contain notebooks and walkthroughs for example workflows.
- `tests/` stores sample inputs and outputs (`tests/pdfs/`, `tests/results/`) used as fixtures rather than automated tests.

## Build, Test, and Development Commands
- Install dependencies:
  - `pip3 install --upgrade -r requirements.txt`
- Configure credentials (local only):
  - Create `.env` with `CHATGPT_API_KEY=...`
- Run against a PDF:
  - `python3 run_pageindex.py --pdf_path /path/to/document.pdf`
- Run against Markdown:
  - `python3 run_pageindex.py --md_path /path/to/document.md`
These commands generate a PageIndex tree structure and write outputs to the working directory.

## Coding Style & Naming Conventions
- Language: Python.
- Indentation: 4 spaces.
- Naming: `snake_case` for functions/variables, `CamelCase` for classes, and lowercase module files.
- Keep new helpers in `pageindex/utils.py` when broadly reusable; keep feature logic close to `page_index.py` / `page_index_md.py`.

## Testing Guidelines
- There is no formal test runner configured in this repo.
- Use `tests/pdfs/` with `run_pageindex.py` to validate output and compare with `tests/results/` when making functional changes.
- For changes affecting parsing or output formatting, include a before/after example in your PR notes.

## Commit & Pull Request Guidelines
- Recent commit messages are short, sentence-style updates (e.g., “Update README.md”).
- Use concise, present-tense summaries; add a short body when the change is non-trivial.
- PRs should describe the change, include example commands run, and link to any related issue or doc update.

## Security & Configuration Tips
- Do not commit API keys or `.env` files.
- Keep example keys redacted in docs and notebooks.
