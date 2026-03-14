#!/usr/bin/env ruby

require 'json'
require 'pathname'
require 'time'
require 'yaml'

ROOT = Pathname(__dir__).join('..').expand_path
RULES_PATH = ROOT.join('harness', 'rules.yaml')
REPORT_PATH = ROOT.join('reports', 'rules-check.json')
REQUIRED_KEYS = %w[id status scope rationale fix_hint enforcement_layer adr].freeze

def fail_with(errors)
  errors.each { |error| warn(error) }
  exit 1
end

data = YAML.load_file(RULES_PATH)
layers = Array(data['planned_enforcement_layers'])
rules = Array(data['rules'])
errors = []

entries = rules.map do |rule|
  missing_keys = REQUIRED_KEYS.reject { |key| rule.key?(key) }
  errors << "#{rule['id'] || '<unknown>'}: missing keys #{missing_keys.join(', ')}" unless missing_keys.empty?

  if rule['enforcement_layer'] && !layers.include?(rule['enforcement_layer'])
    errors << "#{rule['id']}: invalid enforcement_layer #{rule['enforcement_layer']}"
  end

  if rule['status'] == 'active' && (rule['adr'].nil? || rule['adr'].to_s.empty?)
    errors << "#{rule['id']}: active rules must reference an ADR"
  end

  {
    'id' => rule['id'],
    'status' => rule['status'],
    'enforcement_layer' => rule['enforcement_layer'],
    'adr' => rule['adr']
  }
end

fail_with(errors) unless errors.empty?

report = {
  'generated_at' => Time.now.utc.iso8601,
  'tool' => 'scripts/check_rules.rb',
  'rules_file' => 'harness/rules.yaml',
  'enforcement_state' => data['enforcement_state'],
  'planned_enforcement_layers' => layers,
  'entries' => entries
}

REPORT_PATH.dirname.mkpath unless REPORT_PATH.dirname.exist?
REPORT_PATH.write(JSON.pretty_generate(report) + "\n")

puts("Rules structure checks passed for #{entries.length} rule(s)")
puts("Wrote report #{REPORT_PATH.relative_path_from(ROOT)}")
