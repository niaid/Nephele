head -n 1 $1 > header.txt
treatmentcols=($(cat header.txt | perl -pe's/\t/\n/g' | grep -ni "treatment" | sed 's/:.*$//'))
cut -f 1$(printf ",%s" "${treatmentcols[@]}") $1 > rawfile_Map.design

