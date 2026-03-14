#!/usr/bin/env ruby

require 'digest'
require 'json'
require 'pathname'
require 'time'
require 'yaml'

ROOT = Pathname(__dir__).join('..').expand_path
PROJECTION_GLOB = ROOT.join('harness', 'projections', '*.yaml').to_s
DEFAULT_REPORT_PATH = ROOT.join('reports', 'projection-sync.json')

def sha256_for(path)
  Digest::SHA256.file(path).hexdigest
end

def relative_to_root(path)
  path.relative_path_from(ROOT).to_s
end

def fail_with(errors)
  errors.each { |error| warn(error) }
  exit 1
end

errors = []
checked = []
report_entries = []

previous_report = if DEFAULT_REPORT_PATH.exist?
  JSON.parse(DEFAULT_REPORT_PATH.read)
else
  { 'projections' => [] }
end

previous_by_projection = previous_report.fetch('projections', []).each_with_object({}) do |projection, memo|
  projection_path = projection['projection']
  memo[projection_path] = projection if projection_path
end

Dir.glob(PROJECTION_GLOB).sort.each do |projection_path|
  data = YAML.load_file(projection_path)
  target = data.fetch('target', {})
  realization = data.fetch('realization', {})

  output_path = target['output_path']
  mode = realization['mode']
  projection_name = relative_to_root(Pathname(projection_path))

  if output_path.nil? || output_path.empty?
    errors << "#{projection_path}: missing target.output_path"
    next
  end

  if mode.nil? || mode.empty?
    errors << "#{projection_path}: missing realization.mode"
    next
  end

  output = ROOT.join(output_path)
  unless output.exist? || output.symlink?
    errors << "#{projection_path}: target #{output_path} does not exist"
    next
  end

  input_hashes = {}
  missing_inputs = []

  Array(data['inputs']).each do |input_path|
    input = ROOT.join(input_path)
    unless input.exist?
      missing_inputs << input_path
      next
    end

    input_hashes[input_path] = {
      'sha256' => sha256_for(input),
      'kind' => (input.symlink? ? 'symlink' : 'file')
    }
  end

  unless missing_inputs.empty?
    errors << "#{projection_path}: missing input(s): #{missing_inputs.join(', ')}"
    next
  end

  output_metadata = {
    'path' => output_path,
    'kind' => (output.symlink? ? 'symlink' : 'file')
  }

  case mode
  when 'emitted'
    if output.symlink?
      errors << "#{projection_path}: expected #{output_path} to be a regular file, but it is a symlink"
      next
    end
    output_metadata['sha256'] = sha256_for(output)
    checked << "OK emitted #{output_path}"
  when 'symlink'
    unless output.symlink?
      errors << "#{projection_path}: expected #{output_path} to be a symlink"
      next
    end

    canonical_source = realization['canonical_source']
    if canonical_source.nil? || canonical_source.empty?
      errors << "#{projection_path}: symlink mode requires realization.canonical_source"
      next
    end

    expected = ROOT.join(canonical_source).expand_path
    actual = output.realpath

    if actual != expected
      errors << "#{projection_path}: #{output_path} resolves to #{actual.relative_path_from(ROOT)} not #{canonical_source}"
      next
    end

    output_metadata['canonical_source'] = canonical_source
    output_metadata['resolved_path'] = relative_to_root(actual)
    output_metadata['resolved_sha256'] = sha256_for(actual)
    checked << "OK symlink #{output_path} -> #{canonical_source}"
  else
    errors << "#{projection_path}: unsupported realization.mode #{mode.inspect}"
  end

  previous_projection = previous_by_projection[projection_name] || {}
  previous_inputs = previous_projection.fetch('inputs', {})
  changed_inputs = input_hashes.each_with_object([]) do |(input_path, metadata), memo|
    previous_hash = previous_inputs.dig(input_path, 'sha256')
    memo << input_path if previous_hash && previous_hash != metadata['sha256']
  end

  report_entries << {
    'projection' => projection_name,
    'target' => target,
    'realization' => realization,
    'inputs' => input_hashes,
    'output' => output_metadata,
    'changes_since_last_report' => changed_inputs,
    'checked_at' => Time.now.utc.iso8601
  }
end

fail_with(errors) unless errors.empty?

DEFAULT_REPORT_PATH.dirname.mkpath unless DEFAULT_REPORT_PATH.dirname.exist?
report = {
  'generated_at' => Time.now.utc.iso8601,
  'tool' => 'scripts/check_projection_sync.rb',
  'projections' => report_entries
}
DEFAULT_REPORT_PATH.write(JSON.pretty_generate(report) + "\n")

checked.each { |line| puts(line) }
puts("Projection realization checks passed for #{checked.length} target(s)")
puts("Wrote report #{relative_to_root(DEFAULT_REPORT_PATH)}")
