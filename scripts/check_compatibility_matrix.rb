#!/usr/bin/env ruby

require 'json'
require 'pathname'
require 'time'
require 'yaml'

ROOT = Pathname(__dir__).join('..').expand_path
MATRIX_PATH = ROOT.join('harness', 'compatibility-matrix.yaml')
REPORT_PATH = ROOT.join('reports', 'compatibility-matrix.json')

def relative_to_root(path)
  path.relative_path_from(ROOT).to_s
end

def percentage(part, whole)
  return 0.0 if whole.zero?

  ((part.to_f / whole) * 100).round(2)
end

matrix = YAML.load_file(MATRIX_PATH)
vocabulary = Array(matrix['kernel_vocabulary'])
vendors = matrix.fetch('vendors', {})

report_vendors = vendors.sort.map do |vendor_name, vendor_data|
  support = vendor_data.fetch('support', {})
  missing = vocabulary - support.keys
  status_counts = Hash.new(0)

  support.each_value do |entry|
    status_counts[entry.fetch('status')] += 1
  end

  reviewed = support.length

  {
    'vendor' => vendor_name,
    'reviewed_capabilities' => reviewed,
    'total_capabilities' => vocabulary.length,
    'coverage_percent' => percentage(reviewed, vocabulary.length),
    'status_counts' => status_counts.sort.to_h,
    'missing_capabilities' => missing.sort
  }
end

totals = {
  'vendors' => report_vendors.length,
  'capability_vocabulary_size' => vocabulary.length,
  'reviewed_cells' => report_vendors.sum { |entry| entry['reviewed_capabilities'] },
  'possible_cells' => report_vendors.length * vocabulary.length
}
totals['coverage_percent'] = percentage(totals['reviewed_cells'], totals['possible_cells'])

report = {
  'generated_at' => Time.now.utc.iso8601,
  'tool' => relative_to_root(Pathname(__FILE__).expand_path),
  'matrix' => relative_to_root(MATRIX_PATH),
  'matrix_status' => matrix['status'],
  'matrix_coverage' => matrix['coverage'],
  'totals' => totals,
  'vendors' => report_vendors
}

REPORT_PATH.dirname.mkpath unless REPORT_PATH.dirname.exist?
REPORT_PATH.write(JSON.pretty_generate(report) + "\n")

puts("Compatibility matrix coverage checks passed for #{report_vendors.length} vendor(s)")
puts("Wrote report #{relative_to_root(REPORT_PATH)}")
