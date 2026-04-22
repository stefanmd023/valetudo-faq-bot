#!/usr/bin/perl

use strict;
use warnings;
use List::MoreUtils qw(uniq);

my $mdfile = "index.html";

open my $in, "<$mdfile" or die "Could not open '$mdfile': $!\n"
    . "You can fetch it from https://raw.githubusercontent.com/Hypfer/Valetudo/refs/heads/master/docs/pages/general/supported-robots.md\n";

my $outdir = shift;
$outdir =~ s@/$@@ if defined $outdir; 

print "No output directory supplied, just parsing the data!\n" unless defined $outdir;

my %robots;
my $n = 0;

# --- TOC PARSING ---
my $in_toc = 0;
my $manufacturer = "";

print "Starting to parse file: $mdfile\n";

while (my $line = <$in>) {
    ++$n;
    
    if ($line =~ m{<div class="toc">}) {
        print "-> Found TOC section at line $n\n";
        $in_toc = 1;
        next;
    }

    if ($in_toc && $line =~ m{</div>}) {
        print "-> Reached end of TOC section at line $n\n";
        last;
    }

    if ($in_toc) {
        if ($line =~ m{<li><a href="/pages/general/supported-robots/#([^"]+)">([^<]+)</a>}) {
            my $id = $1;
            my $name = $2;

            if ($line =~ m{</a>\s*<ol>}) {
                $manufacturer = $name;
                print "   [Manufacturer] Set current context to: $manufacturer\n";
            } 
            elsif ($manufacturer ne "") {
                die "Duplicate id '$id'!\n" if defined $robots{$id};
                
                $robots{$id} = { 
                    "manufacturer" => $manufacturer,
                    "models" => ["$manufacturer $name"],
                    "models_lines" => [$n],
                    "id" => $id
                };
                print "   [Model] Found robot: $name (ID: $id)\n";
            }
        }
    }
}

# --- BODY PARSING ---
my $bot_id = undef;
my $sold_as = 0;
print "Starting body parsing...\n";

while (my $line = <$in>) {
    ++$n;
    $line =~ s/\s*$//;
    
    if ($line =~ m/^###.*id="([^"]+)"/) {
        $bot_id = $1;
        if (defined $robots{$bot_id}) {
            print "   [Body] Matching ID: $bot_id\n";
        } else {
            die "Bad id at line $n: $bot_id\n";
        }
    } elsif ($line =~ m/.*sold as:\s*$/) {
        $sold_as = 1;
    } elsif ($sold_as == 1 and $line =~ m/- \s*(.*)/) {
        my $as = $1;
        push @{$robots{$bot_id}{"models"}}, $as;
        push @{$robots{$bot_id}{"models_lines"}}, $n;
        print "   [Alias] Added alias for $bot_id: $as\n";
    } elsif ($sold_as == 1) {
        $sold_as = 0;
    }
}

close $in;
print "Parsing complete.\n\n";

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
    
    # Check for duplicates or handle output
    if (-e $fname) {
        print "   ! File $fname already exists, skipping write.\n";
    } else {
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
}