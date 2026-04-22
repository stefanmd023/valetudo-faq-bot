#!/usr/bin/perl

use strict;
use warnings;
use List::MoreUtils qw(uniq);

my $mdfile = "index.html";
open my $in, "<$mdfile" or die "Could not open '$mdfile': $!\n";

my $outdir = shift;
$outdir =~ s@/$@@ if defined $outdir; 

my %robots;
my $n = 0;
my $manufacturer = "";
my $bot_id = undef;
my $sold_as = 0;

while (my $line = <$in>) {
    ++$n;
    
    # 1. Manufacturer (h2)
    if ($line =~ m{<h2[^>]*id="([^"]+)"[^>]*>(.*?)</h2>}) {
        $manufacturer = $2;
    }
    # 2. Model (h3)
    elsif ($line =~ m{<h3[^>]*id="([^"]+)"[^>]*>(.*?)</h3>}) {
        $bot_id = $1;
        my $model_name = $2;
        
        # --- SMART NAME ASSEMBLER ---
        # If manufacturer is already in the name, don't prepend it again.
        my $full_name = ($model_name =~ m/^\s*\Q$manufacturer\E/i) 
                        ? $model_name 
                        : "$manufacturer $model_name";
        
        $robots{$bot_id} = { 
            "manufacturer" => $manufacturer,
            "models" => [$full_name],
            "models_lines" => [$n],
            "id" => $bot_id
        };
        $sold_as = 0;
    }
    # 3. Sold as trigger
    elsif ($line =~ m{sold as:}) {
        $sold_as = 1;
    }
    # 4. Alias list items
    elsif ($sold_as && $line =~ m{<li>(.*?)</li>}) {
        my $alias = $1;
        $alias =~ s/<[^>]*>//g; # Remove nested tags
        push @{$robots{$bot_id}{"models"}}, $alias;
    }
    elsif ($sold_as && $line =~ m{</ul>}) {
        $sold_as = 0;
    }
}
close $in;

# --- KEYWORD GENERATION ---
sub add_keywords {
    my $keywords = shift;
    my $string = shift;
    foreach my $substr (split(" ", lc $string)) {
        next if $substr =~ m/^[^a-z0-9]{1}$/;
        $keywords->{$substr} = 1;
        my $clean = $substr;
        $clean =~ s/[^a-z0-9_]//g;
        $keywords->{$clean} = 1 if ($clean ne "" and $clean ne $substr);
    }
}

# --- OUTPUT GENERATION ---
foreach my $id (sort keys %robots) {
    my %keywords;
    foreach my $model (@{$robots{$id}{"models"}}) {
        add_keywords(\%keywords, $model);
    }
    add_keywords(\%keywords, $id);
    my $keywords = join(", ", sort keys %keywords);

    next unless $outdir;

    my @raw_models = @{$robots{$id}{"models"}};
    my $main_title = $raw_models[0];
    
    # Filter: Get unique models and remove the main_title from the alias list
    my @uniq_models = uniq sort @raw_models;
    @uniq_models = grep { lc($_) ne lc($main_title) } @uniq_models;

    my $fname = "$outdir/$id.txt";
    open my $out, ">$fname" or die "Could not open '$fname': $!\n";
    
    my $aka = "";
    if (scalar @uniq_models > 0) {
        $aka = join ("\n - ", "\nThis robot is also known as:", @uniq_models);
    }

    print $out <<"EOF";
keywords: $keywords
title: $main_title
short-title: $id
text:
You can find rooting information at https://valetudo.cloud/pages/general/supported-robots/#$id$aka
EOF
    close $out;
}