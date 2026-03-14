#!/usr/bin/env ruby

require 'pathname'
require 'yaml'

ROOT = Pathname(__dir__).join('..').expand_path
PROJECTION_GLOB = ROOT.join('harness', 'projections', '*.yaml').to_s

def fail_with(errors)
  errors.each { |error| warn(error) }
  exit 1
end

errors = []
checked = []

Dir.glob(PROJECTION_GLOB).sort.each do |projection_path|
  data = YAML.load_file(projection_path)
  target = data.fetch('target', {})
  realization = data.fetch('realization', {})

  output_path = target['output_path']
  mode = realization['mode']

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

  case mode
  when 'emitted'
    if output.symlink?
      errors << "#{projection_path}: expected #{output_path} to be a regular file, but it is a symlink"
      next
    end
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

    checked << "OK symlink #{output_path} -> #{canonical_source}"
  else
    errors << "#{projection_path}: unsupported realization.mode #{mode.inspect}"
  end
end

fail_with(errors) unless errors.empty?

checked.each { |line| puts(line) }
puts("Projection sync check passed for #{checked.length} target(s)")
