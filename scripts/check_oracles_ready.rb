#!/usr/bin/env ruby

require 'json'
require 'pathname'
require 'time'
require 'yaml'

ROOT = Pathname(__dir__).join('..').expand_path
MANIFEST_PATH = ROOT.join('harness', 'manifest.yaml')
ORACLES_PATH = ROOT.join('harness', 'oracles.yaml')
REPORT_PATH = ROOT.join('reports', 'oracles-readiness.json')
CORE_CHECKS = %w[format lint typecheck unit].freeze

def report_and_exit(report, errors)
  REPORT_PATH.dirname.mkpath unless REPORT_PATH.dirname.exist?
  REPORT_PATH.write(JSON.pretty_generate(report) + "\n")
  if errors.empty?
    if report['stack_selection_status'] == 'complete'
      puts("Oracle readiness checks passed")
    else
      puts("Oracle readiness checks deferred until stack selection is complete")
    end
    puts("Wrote report #{REPORT_PATH.relative_path_from(ROOT)}")
  else
    errors.each { |error| warn(error) }
    puts("Wrote report #{REPORT_PATH.relative_path_from(ROOT)}")
    exit 1
  end
end

manifest = YAML.load_file(MANIFEST_PATH)
oracles = YAML.load_file(ORACLES_PATH)

stack_status = manifest.dig('specialization_record', 'stack_selection', 'status')
harness_status = manifest.dig('specialization_record', 'harness_application', 'status')
quality_commands = manifest.dig('specialization_record', 'harness_application', 'quality_commands') || {}

core_pack = Array(oracles['packs']).find { |pack| pack['id'] == 'core' } || {}
core_checks = Array(core_pack['checks']).select { |check| CORE_CHECKS.include?(check['id']) }

errors = []
missing_core_checks = CORE_CHECKS - core_checks.map { |check| check['id'] }
unless missing_core_checks.empty?
  errors << "core oracle pack is missing checks: #{missing_core_checks.join(', ')}"
end

entries = core_checks.map do |check|
  manifest_entry = quality_commands[check['id']] || {}
  command = manifest_entry['command']
  status = manifest_entry['status']

  if stack_status == 'complete'
    if manifest_entry.empty?
      errors << "missing quality_commands entry for #{check['id']}"
    elsif status.nil? || status.empty?
      errors << "quality_commands.#{check['id']}.status is missing"
    elsif command.nil? || command == 'TBD' || command.to_s.strip.empty?
      errors << "quality_commands.#{check['id']}.command is not ready"
    elsif harness_status == 'complete' && status != 'complete'
      errors << "quality_commands.#{check['id']} must be complete when harness_application.status == complete"
    end
  end

  {
    'check_id' => check['id'],
    'oracle_status' => check['status'],
    'blocked_on' => check['blocked_on'],
    'manifest_status' => status,
    'manifest_command' => command
  }
end

report = {
  'generated_at' => Time.now.utc.iso8601,
  'tool' => 'scripts/check_oracles_ready.rb',
  'manifest' => 'harness/manifest.yaml',
  'oracles' => 'harness/oracles.yaml',
  'stack_selection_status' => stack_status,
  'harness_application_status' => harness_status,
  'entries' => entries,
  'errors' => errors
}

report_and_exit(report, errors)
