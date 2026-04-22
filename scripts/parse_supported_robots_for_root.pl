#!/usr/bin/perl

use strict;
use warnings;
use List::MoreUtils qw(uniq);

# Set the input file
my $mdfile = "index.html";

# Check if file exists
open my $in, "<$mdfile" or die "Could not open '$mdfile': $!\n"
    . "Ensure you have downloaded the full HTML source (e.g., using wget or curl).\n";

# Handle output directory
my $outdir = shift;
$outdir =~ s@/$@@ if defined $outdir; 
print "No output directory supplied, just parsing the data!\n" unless defined $outdir;

my %robots;
my $n = 0;
my $manufacturer = "";
my $bot_id = undef;
my $sold_as = 0;

print "--- Starting HTML Header Scan ---\n";

while (my $line = <$in>) {
    ++$n;
    
    # 1. Look for Manufacturer (h2)
    # Matches: <h2 id="xiaomi" ...>Xiaomi</h2>
    if ($line =~ m{<h2[^>]*id="([^"]+)"[^>]*>(.*?)</h2>}) {
        $manufacturer = $2;
        print "-> [Manufacturer] Set context: $manufacturer\n";
    }

    # 2. Look for Model (h3)
    # Matches: <h3 id="xiaomi-v1" ...>Xiaomi V1</h3>
    elsif ($line =~ m{<h3[^>]*id="([^"]+)"[^>]*>(.*?)</h3>}) {
        $bot_id = $1;
        my $model_name = $2;
        
        $robots{$bot_id} = { 
            "manufacturer" => $manufacturer,
            "models" => ["$manufacturer $model_name"],
            "models_lines" => [$n],
            "id" => $bot_id
        };
        print "   [Model] Found: $model_name (ID: $bot_id)\n";
        $sold_as = 0; # Reset sold_as state for the new model
    }

    # 3. Look for "sold as:" trigger
    elsif ($line =~ m{sold as:}) {
        $sold_as = 1;
    }

    # 4. Look for list items (aliases) if we are in "sold as" mode
    elsif ($sold_as && $line =~ m{<li>(.*?)</li>}) {
        my $alias = $1;
        # Clean up any potential nested tags like <strong> inside the LI
        $alias =~ s/<[^>]*>//g;
        
        push @{$robots{$bot_id}{"models"}}, $alias;
        push @{$robots{$bot_id}{"models_lines"}}, $n;
        print "      [Alias] Added: $alias\n";
    }
    
    # 5. Stop "sold as" mode if we hit a closing list or new section
    elsif ($sold_as && $line =~ m{</ul>}) {
        $sold_as = 0;
    }
}

close $in;
print "--- Parsing Complete. Found " . scalar(keys %robots) . " robots. ---\n\n";

# --- KEYWORD GENERATION ---
sub add_keywords {
    my $keywords = shift;
    my $string = shift;
    foreach my $substr (split(" ", lc $string)) {
        next if $substr =~ m/^[^a-z0-9]{1}$/;
        $keywords->{$substr} = 1;

        my $clean = $substr;
        $clean =~ s/[^a-z0-9_]//g;
        if ($clean ne "" and $clean ne $substr) {
            $keywords->{$clean} = 1;
        }
    }
}

# --- OUTPUT GENERATION ---
foreach my $id (sort keys %robots) {
    print "Processing ID: $id\n";
    $n = 0;
    my %keywords;
    foreach my $model (uniq sort @{$robots{$id}{"models"}}) {
        add_keywords(\%keywords, $model);
        print "  - $model (",$robots{$id}{"models_lines"}[$n],")\n";
        ++$n;
    }
    add_keywords(\%keywords, $id);
    my $keywords = join(", ", sort keys %keywords);
    print "  => Keywords: $keywords\n"; 

    next unless $outdir;

    my @uniq_models = uniq @{$robots{$id}{"models"}};
    @uniq_models = sort @uniq_models;
    my $fname = "$outdir/$id.txt";
    
    open my $out, ">$fname" or die "Could not open '$fname': $!\n";
    my $aka = "";
    if (scalar @uniq_models > 1) {
        $aka = join ("\n - ", "\nThis robot is also known as:", @uniq_models);
    }
    print $out <<"EOF";
keywords: $keywords
title: $robots{$id}{"models"}[0]
short-title: $id
text:
You can find rooting information at https://valetudo.cloud/pages/general/supported-robots/#$id$aka
EOF
    close $out;
    print "   + Created file: $fname\n";
}