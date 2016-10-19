#create plots from Nephele output using phlyoseq
#### USAGE #########

#betterplots.R <biom file> <mapping file as txt> <taxa level for plots> <HMP YES/NO>

##################################################################################
# The possiblity exitsts to add many options for producing custom graphics       #
# we could have a value for metadata colulm which would repace "TreatmentGroup"  #
# we could produce different types of output files (i.e. pdf, jpg, tiff, etc)    #
# having options to change the x axes if desired.                                #
# We could also produce different plots (i.e. diversity, PCoA, etc)              #
# This is just the plain MVP for getting this working.                           #
##################################################################################

#Get packages
library('phyloseq')
library('ggplot2')

#generate ordered bar chart function
plot_ordered_bar<-function (physeq, x = "Sample", 
                            y = "Abundance", 
                            fill = NULL, 
                            leg_size = 0.5,
                            title = NULL) {
  require(ggplot2)
  require(phyloseq)
  require(plyr)
  require(grid)
  bb <- psmelt(physeq)
  
  samp_names <- aggregate(bb$Abundance, by=list(bb$Sample), FUN=sum)[,1]
  .e <- environment()
  bb[,fill]<- factor(bb[,fill], rev(sort(unique(bb[,fill])))) #fill to genus
  
  
  bb<- bb[order(bb[,fill]),] # genus to fill
  p = ggplot(bb, aes_string(x = x, y = y, 
                            fill = fill), 
             environment = .e, ordered = FALSE)
  p = p +geom_bar(stat = "identity", 
                  position = "stack", 
                  color = "black") 
  p = p + theme(axis.text.x = element_text(angle = -90, hjust = 0))
  if (!is.null(title)) {
    p <- p + ggtitle(title)
  }
  return(p)
}

#take command line arguments
args = commandArgs(trailingOnly=TRUE)

if (length(args)==0) {
  stop("At least one argument must be supplied (input file).n", call.=FALSE)
}

biom_file <- args[1]
map_file <- args[2]
taxa_level <- args[3]
OTU_out <- "OTU_table.txt"
HMP <- args[4]

#convert biom file to tsv
biom <- 'biom convert -i '
biom1<- ' -o OTU_table.txt --header-key taxonomy --output-metadata-id ' 
biom3 <- ' --to-tsv'
biom2 <- paste(biom, biom_file, biom1, shQuote("Consensus Lineage"), biom3, sep="")
system(biom2)

#add line to OTU_table.txt
sed_command <- 'echo "" >> OTU_table.txt'
system(sed_command)

#load files into phyloseq
data_to_plot <- import_qiime(otufilename = "OTU_table.txt", mapfilename = map_file, verbose=FALSE)

#merge taxa at the order rank 

#This secion of code fixes the "Rank" vs "Kingdom" issues depending on the different DBs used
ranks_in_data <- rank_names(data_to_plot)

if ((match("Kingdom", ranks_in_data, nomatch= 2))!=1) {
  if ((match("Rank1", ranks_in_data))==1) {
    if(length(ranks_in_data)==6){
      colnames(tax_table(data_to_plot)) = c("Kingdom","Phylum","Class","Order","Family","Genus")
      tax_table(data_to_plot)[, "Phylum"] <- gsub("D_1__", "", tax_table(data_to_plot)[, "Phylum"])
      tax_table(data_to_plot)[, "Class"] <- gsub("D_2__", "", tax_table(data_to_plot)[, "Class"])
      tax_table(data_to_plot)[, "Order"] <- gsub("D_3__", "", tax_table(data_to_plot)[, "Order"])
      tax_table(data_to_plot)[, "Family"] <- gsub("D_4__", "", tax_table(data_to_plot)[, "Family"])
      tax_table(data_to_plot)[, "Genus"] <- gsub("D_5__", "", tax_table(data_to_plot)[, "Genus"])
    }
    else {
      colnames(tax_table(data_to_plot)) = c("Kingdom","Phylum","Class","Order","Family","Genus","Species")
      tax_table(data_to_plot)[, "Phylum"] <- gsub("D_1__", "", tax_table(data_to_plot)[, "Phylum"])
      tax_table(data_to_plot)[, "Class"] <- gsub("D_2__", "", tax_table(data_to_plot)[, "Class"])
      tax_table(data_to_plot)[, "Order"] <- gsub("D_3__", "", tax_table(data_to_plot)[, "Order"])
      tax_table(data_to_plot)[, "Family"] <- gsub("D_4__", "", tax_table(data_to_plot)[, "Family"])
      tax_table(data_to_plot)[, "Genus"] <- gsub("D_5__", "", tax_table(data_to_plot)[, "Genus"])
      tax_table(data_to_plot)[, "Species"] <- gsub("D_6__", "", tax_table(data_to_plot)[, "Species"])
    }  
  }
}

# Remap new names to the ranks_in_data variable before checking the names against the entry
ranks_in_data <- rank_names(data_to_plot)

if (length(grep(paste("^",taxa_level,"$",sep=""), ranks_in_data))==0) {
  cat("\n####################### ERROR #####################\nYour taxa level is not in the data you provided\n")
  cat("Please choose a Rank from the list below:\n\n")
  cat(rank_names(data_to_plot))
  cat("\n\nNOTE!!!! Names are case sensitive.\n\n")
  stop("Bad Rank Name")
}

#collapse OTU table on taxa_level for total abundance metrics and plots
merged_totabund <- tax_glom(data_to_plot, taxrank=taxa_level)


#create relative abundance taxa_levle tables for metrics and plots
relabund <- transform_sample_counts(data_to_plot, function(OTU) OTU/sum(OTU))
merged_relabund <- tax_glom(relabund, taxrank = taxa_level)

#create heatmap if there is more than one sample in the OTU table
#the second line in the if statment renames the title of the x-axis
#total abundance heatmap is also available
num_samples <- dim(sample_data(data_to_plot))[1]
if (num_samples > 1) {
#  heat_plot_total <- plot_heatmap(merged_totabund, "NMDS", "bray", "X.SampleID", taxa_level)
  heat_plot_relative <- plot_heatmap(merged_relabund, "NMDS", "bray", "X.SampleID", taxa_level)
  heat_plot_relative$scales$scales[[1]]$name <- "SampleID"
} 

#Ordered bars plots 
#taxa_image <- plot_ordered_bar(merged, x="X.SampleID",fill = taxa_level)
#taxa_image_ordered_total <- plot_ordered_bar(merged_totabund, x="X.SampleID",fill = taxa_level)
taxa_image_ordered_relative <- plot_ordered_bar(merged_relabund, x="X.SampleID",fill = taxa_level)

#Not Orderd bar plots and standard phyloseq colors
#taxa_image_total <- plot_bar(merged_totabund, x="X.SampleID",fill = taxa_level)
taxa_image_relative <- plot_bar(merged_relabund, x="X.SampleID",fill = taxa_level)

#no facet grids if using plots for HMP as they don't have different TreatmentGroups
if (HMP == "NO") {
  TG_names <- sample_data(data_to_plot)[,"TreatmentGroup"]
  num_of_TGs <- length(unique(TG_names$TreatmentGroup))
  if (num_of_TGs > 1) {
    #facet by taxanomic rank
    #taxa_final_total <- taxa_image_total + theme(legend.position="bottom") + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Total OTU Counts")
    taxa_final_relative <- taxa_image_relative + theme(legend.position="bottom") + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Relative OTU Counts") + xlab("SampleID")

    # facet by treatment group
    #taxa_final_total_TG <- taxa_image_ordered_total + facet_grid(~TreatmentGroup,scales="free",drop=TRUE) + theme(legend.position="bottom") + ggtitle("Total OTU Counts")
    taxa_final_rel_TG <- taxa_image_ordered_relative + facet_grid(~TreatmentGroup,scales="free",drop=TRUE) + theme(legend.position="bottom") + ggtitle("Relative OTU Counts") + xlab("SampleID")
  }
  else {
    #taxa_final_total <- taxa_image_total + theme(legend.position="bottom") + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Total OTU Counts")
    taxa_final_relative <- taxa_image_relative + theme(legend.position="bottom") + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Relative OTU Counts") + xlab("SampleID")
    #only needed if doing facet with TreatmentGroup col
   # taxa_final <- taxa_image + geom_bar(aes_string(color=taxa_level,fill=taxa_level),stat="identity", position="stack") + theme(legend.position="bottom")
  }
}
if (HMP == "YES") {
  #taxa_final_total <- taxa_image_total + theme(legend.position="bottom") + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Total OTU Counts")
  taxa_final_relative <- taxa_image_relative + theme(legend.position="bottom") + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Relative OTU Counts") + xlab("SampleID")
  
  #taxa_final <- taxa_image + geom_bar(aes_string(color=taxa_level,fill=taxa_level),stat="identity", position="stack") + theme(legend.position="bottom") 
}

#save images
#sets up folders and file names and paths
if (HMP == "YES") {
  dir.create("HMP_compare_results/HMP_taxa_plots_and_heatmaps", showWarnings = FALSE)
  dir.create("HMP_compare_results/HMP_taxa_plots_and_heatmaps/mini_barplots" ,showWarnings = FALSE)
  dir.create("HMP_compare_results/HMP_taxa_plots_and_heatmaps/heatmaps" ,showWarnings = FALSE)

  HMP_file <- strsplit(map_file, "/")[[1]]
  HMP_file
  
  heat_name <- paste(noquote(HMP_file[1]),"_heat_map_relative_abundance_",taxa_level,".png", sep="")
  heat_path <- paste("HMP_compare_results","HMP_taxa_plots_and_heatmaps","heatmaps",heat_name, sep="/")
  
  #taxa_name_total <- paste(noquote(HMP_file[1]),"_taxa_plot_total_abundance_",taxa_level,".png",sep="")
  #taxa_path_total <- paste("HMP_compare_results","HMP_taxa_plots_and_heatmaps",taxa_name_total,sep="/")
  
  taxa_name_relative <- paste(noquote(HMP_file[1]),"_taxa_plot_relative_abundance_",taxa_level,".png",sep="")
  taxa_path_relative <- paste("HMP_compare_results","HMP_taxa_plots_and_heatmaps","mini_barplots",taxa_name_relative,sep="/")

  #save tables
  Phylum = 2
  Class = 3
  Order = 4
  Family = 5
  Genus = 6

  dir.create("HMP_compare_results/HMP_taxa_plots_and_heatmaps/taxa_count_tables", showWarnings=FALSE)
  table <- otu_table(merged_totabund)
  rownames(table)=tax_table(merged_totabund)[,taxa_level]
  table_name <- paste(noquote(HMP_file[1]),"_taxa_counts_",taxa_level,".csv", sep="")
  table_path <- paste("HMP_compare_results/HMP_taxa_plots_and_heatmaps/taxa_count_tables",table_name, sep = "/")
  write.csv(table, file = table_path)
}

#different paths if these are not done duing the HMP pipeline
if (HMP == "NO") {
  dir.create("taxa_plots_and_heatmaps" ,showWarnings = FALSE)
  dir.create("taxa_plots_and_heatmaps/stacked_barplots" ,showWarnings = FALSE)
  dir.create("taxa_plots_and_heatmaps/mini_barplots" ,showWarnings = FALSE)
  dir.create("taxa_plots_and_heatmaps/heatmaps" ,showWarnings = FALSE)
  
  heat_name <- paste("heat_map_relative_abundance_",taxa_level,".png", sep="")
  heat_path <- paste("taxa_plots_and_heatmaps/heatmaps",heat_name, sep="/")

  #taxa_name_total <- paste("taxa_plot_total_abundance_",taxa_level,".png",sep="")
  #taxa_path_total <- paste("taxa_plots_and_heatmaps",taxa_name_total,sep="/")
  
  #taxa_name_total_TG <- paste("taxa_plot_total_abundance_by_TreatmentGroup_",taxa_level,".png",sep="")
  #taxa_path_total_TG <- paste("taxa_plots_and_heatmaps",taxa_name_total_TG,sep="/")

  taxa_name_relative <- paste("taxa_plot_relative_abundance_",taxa_level,".png",sep="")
  taxa_path_relative <- paste("taxa_plots_and_heatmaps/mini_barplots",taxa_name_relative,sep="/")

  taxa_name_relative_TG <- paste("taxa_plot_relative_abundance_by_TreatmentGroup_",taxa_level,".png",sep="")
  taxa_path_relative_TG <- paste("taxa_plots_and_heatmaps/stacked_barplots",taxa_name_relative_TG,sep="/")

  #save tables
  Phylum = 2
  Class = 3
  Order = 4
  Family = 5
  Genus = 6

  dir.create("taxa_plots_and_heatmaps/taxa_count_tables", showWarnings=FALSE)
  table <- otu_table(merged_totabund)
  rownames(table)=tax_table(merged_totabund)[,taxa_level]
  table_name <- paste("taxa_counts_",taxa_level,".csv", sep="")
  table_path <- paste("taxa_plots_and_heatmaps/taxa_count_tables",table_name, sep = "/")
  write.csv(table, file = table_path)
}

#--------------------------   PLOTS  -----------------------------------------------------------

#set Width for all tax
graph_width_tax <- (dim(sample_data(merged_totabund))[1])

if (graph_width_tax >= 10) {
  graph_width_tax <- ((dim(sample_data(merged_totabund))[1])*600)
} else if(graph_width_tax > 50) {
  graph_width_tax <- ((dim(sample_data(merged_totabund))[1])*400)
} else {
  graph_width_tax <- ((dim(sample_data(merged_totabund))[1])*800)
}

#set width for heat
graph_width_heat <- dim(sample_data(merged_totabund))[1]

if (graph_width_heat >= 10) {
  graph_width_heat <- ((dim(sample_data(merged_totabund))[1])*300)
} else if(graph_width_heat > 50) {
  graph_width_heat <- ((dim(sample_data(merged_totabund))[1])*200)
} else {
  graph_width_heat <- ((dim(sample_data(merged_totabund))[1])*400)
}

#set minimums
if (graph_width_heat > 1700) {
  graph_width_heat <- 1700
}

if (graph_width_tax > 4000) {
  graph_width_tax <- 4000
}

# set height for heat map
graph_height_heat <- ((dim(tax_table(merged_totabund))[1])*45)

if (graph_height_heat < 1200) {
  graph_height_heat <- 1200
} else {
  graph_height_heat <- ((dim(tax_table(merged_totabund))[1])*45)
}

if (num_samples > 1) {
  print({
    png(filename=heat_path, width=graph_width_heat, height=graph_height_heat, units="px",res=300)
    heat_plot_relative
  })
  dev.off()
}

#set height for taxa plots
graph_height_tax <- ((dim(tax_table(merged_totabund))[1])*92)

if (graph_height_tax < 3700) {
  graph_height_tax <- 3700
} else {
  graph_height_tax <- ((dim(tax_table(merged_totabund))[1])*92)
}


# png(filename=taxa_path_total, width=(dim(sample_data(merged_totabund))[1])*1000, height=graph_height_tax, units="px",res=300)
# taxa_final_total
# dev.off()

png(filename=taxa_path_relative, width=graph_width_tax, height=graph_height_tax, units="px",res=300)
taxa_final_relative
dev.off()

if (HMP == "NO") {
  if (num_of_TGs > 1) {
    print({
      png(filename=taxa_path_relative_TG, width=graph_width_tax, height=graph_height_tax, units="px",res=300)
      taxa_final_rel_TG
    })
    dev.off()
  }
}

# if (num_of_TGs > 1) {
#   print({
#     png(filename=taxa_path_total_TG, width=(dim(sample_data(merged_totabund))[1])*1000, height=graph_height_tax, units="px",res=300)
#     taxa_final_total_TG
#   })
#   dev.off()
# }