#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

CHECK_ONLY=false

log_info() {
    printf '[INFO] %s\n' "$*"
}

log_warn() {
    printf '[WARN] %s\n' "$*" >&2
}

log_error() {
    printf '[ERROR] %s\n' "$*" >&2
}

on_error() {
    local exit_code=$?
    log_error "Setup failed (exit=${exit_code})."
    exit "${exit_code}"
}

trap on_error ERR

usage() {
    cat <<'EOF'
Usage:
  ./scripts/setup.sh
  ./scripts/setup.sh --check

Options:
  --check      Check prerequisites only.
               Do not install tools, sync dependencies, or create .env.

  -h, --help   Show this help.

Examples:
  ./scripts/setup.sh --check
  ./scripts/setup.sh
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check)
            CHECK_ONLY=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 2
            ;;
    esac
done

cd "${PROJECT_ROOT}"

log_info "Project root: ${PROJECT_ROOT}"

# -----------------------------------------------------------------------------
# 1. Basic project checks
# -----------------------------------------------------------------------------

if [[ ! -f "${PROJECT_ROOT}/README.md" ]]; then
    log_error "README.md not found."
    exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/mise.toml" ]]; then
    log_error "mise.toml not found."
    exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/pyproject.toml" ]]; then
    log_error "pyproject.toml not found."
    exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/scripts/validate.sh" ]]; then
    log_error "scripts/validate.sh not found."
    exit 1
fi

# -----------------------------------------------------------------------------
# 2. Prerequisite checks
# -----------------------------------------------------------------------------

required_commands=(
    git
    mise
)

missing=0

for command_name in "${required_commands[@]}"; do
    if command -v "${command_name}" >/dev/null 2>&1; then
        command_path="$(command -v "${command_name}")"
        log_info "Found: ${command_name} (${command_path})"
    else
        log_error "Required command not found: ${command_name}"
        missing=1
    fi
done

if [[ "${missing}" -ne 0 ]]; then
    log_error "Install the missing prerequisites before continuing."
    exit 1
fi

# -----------------------------------------------------------------------------
# 3. Check-only mode
# -----------------------------------------------------------------------------

if [[ "${CHECK_ONLY}" == true ]]; then
    log_info "Checking mise configuration..."

    if ! mise current >/dev/null 2>&1; then
        log_warn "mise configuration exists, but one or more tools may not be installed yet."
    else
        mise current
    fi

    log_info "Prerequisite check completed successfully."
    exit 0
fi

# -----------------------------------------------------------------------------
# 4. Install runtime tools
# -----------------------------------------------------------------------------

log_info "Installing tool versions defined in mise.toml..."

mise install

log_info "Resolved tool versions:"
mise current

# -----------------------------------------------------------------------------
# 5. Verify uv through mise
# -----------------------------------------------------------------------------

if ! mise exec -- command -v uv >/dev/null 2>&1; then
    log_error "uv could not be resolved through mise."
    exit 1
fi

UV_PATH="$(mise exec -- command -v uv)"
log_info "Using uv: ${UV_PATH}"

log_info "Python version:"
mise exec -- uv run python --version

# -----------------------------------------------------------------------------
# 6. Synchronize Python dependencies
# -----------------------------------------------------------------------------

log_info "Synchronizing Python dependencies..."

if [[ -f "${PROJECT_ROOT}/uv.lock" ]]; then
    log_info "uv.lock found. Using frozen dependency sync."
    mise exec -- uv sync --frozen
else
    log_warn "uv.lock not found."
    log_warn "A new lock file will be generated."
    mise exec -- uv sync
fi

# -----------------------------------------------------------------------------
# 7. Environment file
# -----------------------------------------------------------------------------

ENV_EXAMPLE="${PROJECT_ROOT}/.env.example"
ENV_FILE="${PROJECT_ROOT}/.env"

if [[ -f "${ENV_EXAMPLE}" ]]; then
    if [[ ! -f "${ENV_FILE}" ]]; then
        log_info "Creating .env from .env.example..."

        cp "${ENV_EXAMPLE}" "${ENV_FILE}"
        chmod 600 "${ENV_FILE}"

        log_warn ".env was created."
        log_warn "Set the required API keys before running external API calls."
    else
        log_info ".env already exists; leaving it unchanged."

        current_mode="$(stat -c '%a' "${ENV_FILE}" 2>/dev/null || true)"

        if [[ "${current_mode}" != "600" ]]; then
            log_warn ".env permissions are ${current_mode:-unknown}; recommended mode is 600."
        fi
    fi
else
    log_warn ".env.example does not exist."
    log_warn "No .env file was created."
fi

# -----------------------------------------------------------------------------
# 8. Verify .env is ignored by Git
# -----------------------------------------------------------------------------

if [[ -f "${ENV_FILE}" ]]; then
    if git check-ignore -q "${ENV_FILE}"; then
        log_info ".env is excluded from Git."
    else
        log_error ".env is NOT excluded from Git."
        log_error "Update .gitignore before continuing."
        exit 1
    fi
fi

# -----------------------------------------------------------------------------
# 9. Run validation
# -----------------------------------------------------------------------------

log_info "Running project validation..."

"${PROJECT_ROOT}/scripts/validate.sh"

# -----------------------------------------------------------------------------
# 10. Summary
# -----------------------------------------------------------------------------

log_info "Setup completed successfully."

cat <<'EOF'

Next steps:

  1. Edit .env and set required API keys.

  2. Load environment variables:

       set -a
       source .env
       set +a

  3. Run the Agent:

       uv run python -m agent_lab.main

  4. Re-run validation when needed:

       ./scripts/validate.sh

EOF
