#!/usr/bin/perl

use strict;
use warnings;
use List::MoreUtils qw(uniq);

my $mdfile = "index.html";

open my $in, "<$mdfile" or die "Could not open '$mdfile': $!\n"
    . "You can fetch it from https://valetudo.cloud/pages/general/supported-robots/\n";

my $outdir = shift;
$outdir =~ s@/$@@ if defined $outdir; 

print "No output directory supplied, just parsing the data!\n" unless defined $outdir;

my %robots;
my $n = 0;

# --- NEW TOC PARSING LOGIC ---
my $in_toc = 0;
my $manufacturer = "";

while (my $line = <$in>) {
    ++$n;
    
    # 1. Gatekeeper: Start parsing
    if ($line =~ m{<div class="toc">}) {
        $in_toc = 1;
        next;
    }

    # 2. Gatekeeper: Stop parsing
    if ($in_toc && $line =~ m{</div>}) {
        last;
    }

    # 3. Only parse if we are inside the TOC div
    if ($in_toc) {
        # Match list items containing links
        if ($line =~ m{<li><a href="/pages/general/supported-robots/#([^"]+)">([^<]+)</a>}) {
            my $id = $1;
            my $name = $2;

            # If the entry is followed by an <ol>, it's a Manufacturer (a category header)
            if ($line =~ m{</a>\s*<ol>}) {
                $manufacturer = $name;
            } 
            # Otherwise, it's a model belonging to the current manufacturer
            elsif ($manufacturer ne "") {
                die "Duplicate id '$id'!\n" if defined $robots{$id};
                
                $robots{$id} = { 
                    "manufacturer" => $manufacturer,
                    "models" => ["$manufacturer $name"],
                    "models_lines" => [$n],
                    "id" => $id
                };
            }
        }
    }
}

# --- REMAINING BODY PARSING ---
my $bot_id = undef;
my $sold_as = 0;
while (my $line = <$in>) {
    ++$n;
    $line =~ s/\s*$//;
    if ($line =~ m/^###.*id="([^"]+)"/) {
        $bot_id = $1;
        die "Bad id at line $n: $bot_id\n" unless defined $robots{$bot_id};
    } elsif ($line =~ m/.*sold as:\s*$/) {
        $sold_as = 1;
    } elsif ($sold_as == 1 and $line =~ m/- \s*(.*)/) {
        my $as = $1;
        push @{$robots{$bot_id}{"models"}}, $as;
        push @{$robots{$bot_id}{"models_lines"}}, $n;
    } elsif ($sold_as == 1) {
        $sold_as = 0;
    }
}

close $in;

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
    print "ID: $id\n";
    $n = 0;
    my %keywords;
    foreach my $model (uniq sort @{$robots{$id}{"models"}}) {
        add_keywords(\%keywords, $model);
        print "  - $model (",$robots{$id}{"models_lines"}[$n],")\n";
        ++$n;
    }
    add_keywords(\%keywords, $id);
    my $keywords = join(", ", sort keys %keywords);
    print "  => $keywords\n"; 

    next unless $outdir;

    my @uniq_models = uniq @{$robots{$id}{"models"}};
    @uniq_models = sort @uniq_models;
    my $fname = "$outdir/$id.txt";
    die "Duplicate filename '$fname'!" if -e $fname;
    open my $out, ">$fname" or die "Could not open '$fname': $!\n";
    my $aka = "";
    if (scalar @uniq_models > 1) {
        $aka = join ("\n - ", "\nThis robot is also known as:", @uniq_models);
    }
    print $out <<"EOF"
keywords: $keywords
title: $robots{$id}{"models"}[0]
short-title: $id
text:
You can find rooting information at https://valetudo.cloud/pages/general/supported-robots/#$id$aka
EOF
    ;
    close $out;
}